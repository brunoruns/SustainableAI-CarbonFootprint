"""Tests voor de niet-functionele vereisten (NFR-1 t/m NFR-4)."""

import json
import re
import socket
import sys
import time
import tomllib
from pathlib import Path

import pytest

from structuur_detectie import parseer


def test_nfr1_detectie_en_parsing_verlaat_nooit_het_apparaat(
    openai_export: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def blokkeer(*args: object, **kwargs: object) -> None:
        raise RuntimeError("netwerkverkeer geblokkeerd in de test")

    monkeypatch.setattr(socket, "socket", blokkeer)
    monkeypatch.setattr(socket, "create_connection", blokkeer)
    gesprekken = parseer(openai_export)
    assert gesprekken


def test_nfr2_export_van_1000_gesprekken_wordt_binnen_twee_minuten_verwerkt(tmp_path: Path) -> None:
    exporter = tmp_path / "chat-export-1700000000000"
    exporter.mkdir()
    for volgnummer in range(1000):
        berichten = [
            {
                "id": f"m-{volgnummer}-1",
                "chatId": f"chat-{volgnummer}",
                "content": "vraag",
                "role": "user",
                "createdAt": "2024-01-01T00:00:00.000Z",
            },
            {
                "id": f"m-{volgnummer}-2",
                "chatId": f"chat-{volgnummer}",
                "content": "antwoord",
                "role": "assistant",
                "createdAt": "2024-01-01T00:00:01.000Z",
            },
        ]
        bestand = exporter / f"chat-{volgnummer:04d}.json"
        bestand.write_text(json.dumps(berichten), encoding="utf-8")
    start = time.monotonic()
    gesprekken = parseer(exporter)
    duur = time.monotonic() - start
    assert len(gesprekken) == 1000
    assert duur < 120.0


def test_nfr3_alleen_de_standaardbibliotheek_wordt_geimporteerd() -> None:
    bron_map = Path(__file__).parents[1] / "src" / "structuur_detectie"
    patroon = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.MULTILINE)
    for pad in bron_map.glob("*.py"):
        tekst = pad.read_text(encoding="utf-8")
        for overeenkomst in patroon.finditer(tekst):
            module = overeenkomst.group(1)
            if module == "structuur_detectie":
                continue
            assert (
                module in sys.stdlib_module_names
            ), f"niet-standaard import: {module} in {pad.name}"


def test_nfr3_project_heeft_alleen_ecologits_als_runtime_dependency() -> None:
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    with pyproject.open("rb") as bestand:
        config = tomllib.load(bestand)
    assert config["project"]["dependencies"] == ["ecologits>=0.10.2,<1.0.0"]


def test_nfr4_vereist_python_3_12_of_nieuwer() -> None:
    assert sys.version_info >= (3, 12)
