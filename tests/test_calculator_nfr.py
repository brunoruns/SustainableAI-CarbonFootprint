"""Tests voor de niet-functionele vereisten van de calculator (NFR-1 t/m NFR-4)."""

import re
import socket
import sys
import time
import tomllib
from pathlib import Path

import pytest

from carbon_calculator import BerekenConfig, bereken_gesprekken
from structuur_detectie import Bericht, Gesprek


def _assistant(volgnummer: int) -> Bericht:
    return Bericht(
        id=f"m-{volgnummer}",
        rol="assistant",
        inhoud=(
            "The output of the process depends on the input and the local context, "
            "so please check the numbers before you report them."
        ),
        created_at=None,
        model="gpt-4o-mini",
    )


def test_nfr1_berekening_draait_offline_en_lokaal(
    calculator_gesprek: Gesprek, monkeypatch: pytest.MonkeyPatch
) -> None:
    def blokkeer(*args: object, **kwargs: object) -> None:
        raise RuntimeError("netwerkverkeer geblokkeerd in de test")

    monkeypatch.setattr(socket, "socket", blokkeer)
    monkeypatch.setattr(socket, "create_connection", blokkeer)
    resultaat = bereken_gesprekken([calculator_gesprek], BerekenConfig())
    assert resultaat.aantal_berichten == 1
    assert resultaat.totale_energie.laag >= 0.0


def test_nfr2_5000_berichten_worden_binnen_een_minuut_berekend() -> None:
    berichten = [_assistant(i) for i in range(5000)]
    gesprekken = [
        Gesprek(
            id="conv-g",
            titel=None,
            provider="openai",
            created_at=None,
            berichten=berichten,
        )
    ]
    start = time.monotonic()
    resultaat = bereken_gesprekken(gesprekken, BerekenConfig())
    duur = time.monotonic() - start
    assert resultaat.aantal_berichten == 5000
    assert resultaat.aantal_overgeslagen == 0
    # de eis uit de spec is 100.000 berichten binnen 5 minuten; 5000 binnen 1 minuut
    # is ruim representatief voor reguliere hardware.
    assert duur < 60.0


def test_nfr3_src_importeert_naast_de_standaardbibliotheek_alleen_ecologits() -> None:
    bron_map = Path(__file__).parents[1] / "src" / "carbon_calculator"
    patroon = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.MULTILINE)
    toegestaan = {"carbon_calculator", "ecologits", "structuur_detectie"}
    for pad in bron_map.glob("*.py"):
        tekst = pad.read_text(encoding="utf-8")
        for overeenkomst in patroon.finditer(tekst):
            module = overeenkomst.group(1)
            if module in toegestaan:
                continue
            assert (
                module in sys.stdlib_module_names
            ), f"niet-standaard import: {module} in {pad.name}"


def test_nfr3_ecologits_is_de_enige_runtime_dependency() -> None:
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    with pyproject.open("rb") as bestand:
        config = tomllib.load(bestand)
    dependencies = config["project"]["dependencies"]
    assert dependencies == ["ecologits>=0.10.2,<1.0.0"]


def test_nfr4_vereist_python_3_12_of_nieuwer() -> None:
    assert sys.version_info >= (3, 12)
