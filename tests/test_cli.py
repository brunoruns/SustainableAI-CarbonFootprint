"""Tests voor de CLI `co2chat` (specs/spec_cli.md).

Spec-first: deze tests definiëren het publieke contract van de CLI. Bedekt
FR-1 t/m FR-6 en NFR-1, NFR-3 en NFR-5, plus de Definition of Done (het
console-script in `pyproject.toml` en de versievlag).
"""

import argparse
import json
import re
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

from bulk_analyser import analyseer, genereeer_json, vind_aanbieders
from carbon_calculator import BerekenConfig
from cli.main import _bouw_config, main


def test_fr1_basis_print_het_markdown_rapport_naar_stdout(
    openai_export: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main([str(openai_export)])

    uitvoer = capsys.readouterr()
    assert code == 0
    assert "methode en bronnen" in uitvoer.out.lower()


def test_fr2_json_is_identiek_aan_genereeer_json(
    openai_export: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main([str(openai_export), "--json"])

    uitvoer = capsys.readouterr()
    assert code == 0
    assert json.loads(uitvoer.out)
    assert uitvoer.out == genereeer_json(analyseer(openai_export))


def test_fr3_output_gaat_naar_bestand_en_niet_naar_stdout(
    openai_export: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    doel = tmp_path / "rapport.json"
    code = main([str(openai_export), "--json", "-o", str(doel)])

    uitvoer = capsys.readouterr()
    assert code == 0
    assert uitvoer.out == ""
    assert doel.read_text(encoding="utf-8") == genereeer_json(analyseer(openai_export))


def test_fr3_bestaand_bestand_wordt_overschreven(
    openai_export: Path, tmp_path: Path
) -> None:
    doel = tmp_path / "rapport.md"
    doel.write_text("oud", encoding="utf-8")

    code = main([str(openai_export), "-o", str(doel)])

    assert code == 0
    inhoud = doel.read_text(encoding="utf-8")
    assert "oud" not in inhoud
    assert "methode en bronnen" in inhoud.lower()


def test_fr3_het_formaat_volgt_de_extensie(
    openai_export: Path, tmp_path: Path
) -> None:
    json_doel = tmp_path / "rapport.json"
    assert main([str(openai_export), "-o", str(json_doel)]) == 0
    assert json.loads(json_doel.read_text(encoding="utf-8"))

    md_doel = tmp_path / "rapport.md"
    assert main([str(openai_export), "-o", str(md_doel)]) == 0
    assert "methode en bronnen" in md_doel.read_text(encoding="utf-8").lower()


def test_fr4_zonder_vlaggen_is_de_config_de_default(openai_export: Path) -> None:
    args = argparse.Namespace(zone=None, model=None, fallback_model=None)
    assert _bouw_config(args, str(openai_export)) == BerekenConfig()


def test_fr4_zone_vult_elke_aanbieder(mistral_export: Path) -> None:
    args = argparse.Namespace(zone="EEE", model=None, fallback_model=None)
    config = _bouw_config(args, str(mistral_export))

    assert config.zones_per_provider == {"mistral": "EEE"}
    assert config.provider_standaard_modellen == {}
    assert config.fallback_model is None


def test_fr4_model_vult_elke_aanbieder(mistral_export: Path) -> None:
    args = argparse.Namespace(zone=None, model="mistral-large-2512", fallback_model=None)
    config = _bouw_config(args, str(mistral_export))

    assert config.provider_standaard_modellen == {"mistral": "mistral-large-2512"}
    assert config.zones_per_provider == {}
    assert config.fallback_model is None


def test_fr4_fallback_model_wordt_doorgegeven(mistral_export: Path) -> None:
    args = argparse.Namespace(zone=None, model=None, fallback_model="gpt-4o-mini")
    config = _bouw_config(args, str(mistral_export))

    assert config.fallback_model == "gpt-4o-mini"
    assert config.zones_per_provider == {}
    assert config.provider_standaard_modellen == {}


def test_fr4_alle_vlaggen_tellen_mee(mistral_export: Path) -> None:
    args = argparse.Namespace(
        zone="EEE", model="mistral-large-2512", fallback_model="gpt-4o-mini"
    )
    config = _bouw_config(args, str(mistral_export))

    assert config.zones_per_provider == {"mistral": "EEE"}
    assert config.provider_standaard_modellen == {"mistral": "mistral-large-2512"}
    assert config.fallback_model == "gpt-4o-mini"


def test_fr4_model_staat_in_het_rapport(
    mistral_export: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main([str(mistral_export), "--model", "mistral-large-2512", "--json"])

    uitvoer = capsys.readouterr()
    assert code == 0
    data = json.loads(uitvoer.out)
    assert data["methode_en_bronnen"]["aantal_overgeslagen"] == 0
    assert data["methode_en_bronnen"]["aantal_zonder_model"] == 3


def test_fr4_zone_staat_in_het_rapport(
    openai_export: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main([str(openai_export), "--zone", "EEE", "--json"])

    uitvoer = capsys.readouterr()
    assert code == 0
    met_zone = json.loads(uitvoer.out)
    zonder_zone = json.loads(genereeer_json(analyseer(openai_export)))
    assert (
        met_zone["totaal"]["uitstoot"]["gemiddelde"]
        != zonder_zone["totaal"]["uitstoot"]["gemiddelde"]
    )


def test_fr5_niet_bestaand_pad_geeft_exit_1_zonder_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main([str(tmp_path / "bestaat-niet")])

    uitvoer = capsys.readouterr()
    assert code == 1
    assert "bestaat-niet" in uitvoer.err
    assert "Traceback" not in uitvoer.err


def test_fr5_ongeldige_zone_geeft_exit_1_zonder_traceback(
    openai_export: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main([str(openai_export), "--zone", "XYZ", "--json"])

    uitvoer = capsys.readouterr()
    assert code == 1
    assert "zone" in uitvoer.err.lower()
    assert "Traceback" not in uitvoer.err


def test_fr5_io_fout_bij_schrijven_geeft_exit_1(
    openai_export: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blokkade = tmp_path / "blokkade"
    blokkade.write_text("geen map", encoding="utf-8")

    code = main([str(openai_export), "-o", str(blokkade / "rapport.md")])

    uitvoer = capsys.readouterr()
    assert code == 1
    assert uitvoer.err.strip()
    assert "Traceback" not in uitvoer.err


def test_fr6_zonder_argumenten_geeft_exit_2() -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_fr6_onbekende_optie_geeft_exit_2() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--onbekende-optie"])
    assert exc.value.code == 2


def test_fr6_json_en_markdown_sluiten_elkaar_uit(openai_export: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        main([str(openai_export), "--json", "--markdown"])
    assert exc.value.code == 2


def test_fr6_version_print_de_versie_en_stopt_met_exit_0(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["-V"])
    assert exc.value.code == 0
    uitvoer = capsys.readouterr().out
    assert uitvoer.startswith("co2chat ")
    assert uitvoer.strip()


def test_nfr1_cli_gebruikt_alleen_standaardbibliotheek_en_projectmodules() -> None:
    bron_map = Path(__file__).parents[1] / "src" / "cli"
    patroon = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.MULTILINE)
    project = {"bulk_analyser", "carbon_calculator", "structuur_detectie", "cli"}
    for pad in bron_map.glob("*.py"):
        tekst = pad.read_text(encoding="utf-8")
        for overeenkomst in patroon.finditer(tekst):
            module = overeenkomst.group(1)
            if module in project:
                continue
            assert (
                module in sys.stdlib_module_names
            ), f"niet-standaard import: {module} in {pad.name}"


def test_nfr3_twee_runs_geven_identieke_output(
    openai_export: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    eerste = main([str(openai_export), "--json"])
    eerste_uitvoer = capsys.readouterr().out
    tweede = main([str(openai_export), "--json"])
    tweede_uitvoer = capsys.readouterr().out

    assert eerste == tweede == 0
    assert eerste_uitvoer == tweede_uitvoer


def test_nfr5_cli_uitspraken_gelijk_aan_directe_module_aanroep(
    mistral_export: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = BerekenConfig(provider_standaard_modellen={"mistral": "mistral-large-2512"})
    verwacht = genereeer_json(analyseer(mistral_export, config))

    code = main([str(mistral_export), "--model", "mistral-large-2512", "--json"])

    uitvoer = capsys.readouterr()
    assert code == 0
    assert uitvoer.out == verwacht


def test_vind_aanbieders_detecteert_elke_export(
    openai_export: Path, mistral_export: Path
) -> None:
    assert vind_aanbieders(openai_export) == ("openai",)
    assert vind_aanbieders(mistral_export) == ("mistral",)


def test_vind_aanbieders_werkt_ook_op_een_zip(
    mistral_export: Path, tmp_path: Path
) -> None:
    zip_pad = tmp_path / "chat-export.zip"
    with zipfile.ZipFile(zip_pad, "w") as archief:
        for bestand in mistral_export.rglob("*"):
            if bestand.is_file():
                archief.write(bestand, bestand.relative_to(mistral_export.parent))

    assert vind_aanbieders(zip_pad) == ("mistral",)


def test_dod_cli_is_geregistreerd_als_console_script() -> None:
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    with pyproject.open("rb") as bestand:
        config = tomllib.load(bestand)
    assert config["project"]["scripts"]["co2chat"] == "cli.main:main"
