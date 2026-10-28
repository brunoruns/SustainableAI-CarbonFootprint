"""Niet-functionele tests voor de bulk analyser (NFR-1 t/m NFR-5)."""

import json
import re
import socket
import sys
import time
from pathlib import Path

import pytest

from bulk_analyser import analyseer
from carbon_calculator import BerekenConfig, WaardeBereik


def test_nfr1_pijplijn_verlaat_nooit_het_apparaat(
    openai_export: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def blokkeer(*args: object, **kwargs: object) -> None:
        raise RuntimeError("netwerkverkeer geblokkeerd in de test")

    monkeypatch.setattr(socket, "socket", blokkeer)
    monkeypatch.setattr(socket, "create_connection", blokkeer)

    rapport = analyseer(openai_export)
    assert rapport.aantal_gesprekken == 2


def test_nfr2_export_van_een_jaar_wordt_binnen_vijf_minuten_verwerkt(
    tmp_path: Path,
) -> None:
    export = tmp_path / "chat-export-1700000000000"
    export.mkdir()
    for volgnummer in range(1000):
        maand = (volgnummer % 12) + 1
        tijd = f"2024-{maand:02d}-{volgnummer % 28 + 1:02d}T10:00:00.000Z"
        chat_id = f"chat-{volgnummer}"
        berichten = [
            {
                "id": f"m-{volgnummer}-1",
                "chatId": chat_id,
                "content": "Wat is de opbrengst van zonnepanelen in deze maand?",
                "role": "user",
                "createdAt": tijd,
            },
            {
                "id": f"m-{volgnummer}-2",
                "chatId": chat_id,
                "content": "De opbrengst hangt af van de locatie en het seizoen.",
                "role": "assistant",
                "createdAt": tijd,
            },
        ]
        bestand = export / f"chat-{volgnummer:04d}.json"
        bestand.write_text(json.dumps(berichten), encoding="utf-8")

    config = BerekenConfig(provider_standaard_modellen={"mistral": "mistral-large-2512"})
    start = time.monotonic()
    rapport = analyseer(export, config)
    duur = time.monotonic() - start

    assert rapport.aantal_gesprekken == 1000
    assert rapport.aantal_berichten == 1000
    # de eis uit de spec is 1000 gesprekken binnen 5 minuten
    assert duur < 300.0


def test_nfr3_bulk_analyser_gebruikt_alleen_standaardbibliotheek() -> None:
    bron_map = Path(__file__).parents[1] / "src" / "bulk_analyser"
    patroon = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.MULTILINE)
    toegestaan = {"bulk_analyser", "structuur_detectie", "carbon_calculator"}
    for pad in bron_map.glob("*.py"):
        tekst = pad.read_text(encoding="utf-8")
        for overeenkomst in patroon.finditer(tekst):
            module = overeenkomst.group(1)
            if module in toegestaan:
                continue
            assert (
                module in sys.stdlib_module_names
            ), f"niet-standaard import: {module} in {pad.name}"


def test_nfr4_vereist_python_3_12_of_nieuwer() -> None:
    assert sys.version_info >= (3, 12)


def _openai_conversatie_zonder_model() -> dict[str, object]:
    """Eén openai-gesprek met een assistant-bericht zonder model_slug."""
    return {
        "id": "conv-onbekend",
        "title": "Zonder model",
        "create_time": 1733294339.556244,
        "current_node": "node-assistent",
        "mapping": {
            "node-wortel": {
                "id": "node-wortel",
                "message": None,
                "parent": None,
                "children": ["node-gebruiker"],
            },
            "node-gebruiker": {
                "id": "node-gebruiker",
                "message": {
                    "id": "msg-gebruiker",
                    "author": {"role": "user", "name": None, "metadata": {}},
                    "create_time": 1733294335.0,
                    "content": {"content_type": "text", "parts": ["Leg het kort uit."]},
                    "metadata": {},
                },
                "parent": "node-wortel",
                "children": ["node-assistent"],
            },
            "node-assistent": {
                "id": "node-assistent",
                "message": {
                    "id": "msg-onbekend",
                    "author": {"role": "assistant", "name": None, "metadata": {}},
                    "create_time": 1733294339.5,
                    "content": {
                        "content_type": "text",
                        "parts": ["Een antwoord zonder modelinformatie."],
                    },
                    "metadata": {},
                },
                "parent": "node-gebruiker",
                "children": [],
            },
        },
    }


def test_nfr5_overgeslagen_berichten_staan_expliciet_in_het_rapport(
    tmp_path: Path,
) -> None:
    # een openai-bericht zonder model_slug heeft attributie 'onbekend' en wordt
    # zonder fallback overgeslagen; dat moet met reden in het rapport staan.
    export = tmp_path / "openai"
    export.mkdir()
    (export / "conversations.json").write_text(
        json.dumps([_openai_conversatie_zonder_model()]), encoding="utf-8"
    )
    rapport = analyseer(export, BerekenConfig())

    assert rapport.aantal_berichten == 1
    overgeslagen = rapport.overgeslagen
    assert len(overgeslagen) == 1
    item = overgeslagen[0]
    assert item.bericht_id == "msg-onbekend"
    assert item.gesprek_id
    assert item.reden.strip()

    assert rapport.methode.aantal_overgeslagen == 1
    # geen stil verkeerde output: het totaal is nul, niet zomaar verdwenen.
    assert rapport.aggregaten.totaal.energie == WaardeBereik(0.0, 0.0, 0.0)
    assert rapport.aggregaten.totaal.requests == 1


def test_nfr5_mistral_telt_standaard_mee_via_het_basismodel(
    mistral_export: Path,
) -> None:
    # mistral-berichten hebben geen model; via het standaard basismodel uit de
    # config worden ze nu meegeteld in plaats van overgeslagen (FR-7).
    rapport = analyseer(mistral_export, BerekenConfig())

    assert rapport.aantal_berichten == 3
    assert len(rapport.overgeslagen) == 0
    assert rapport.methode.aantal_overgeslagen == 0
    assert rapport.aggregaten.totaal.requests == 3
    assert rapport.aggregaten.totaal.energie != WaardeBereik(0.0, 0.0, 0.0)
