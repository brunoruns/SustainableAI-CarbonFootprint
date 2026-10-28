"""Tests voor de pijplijn en het rapport van de bulk analyser.

Deze tests definiëren het publieke contract van `bulk_analyser.analyseer`,
`genereeer_json`, `genereeer_markdown` en `AnalyseFout`, nog zonder dat de
module is geïmplementeerd (spec-first). Bedekt FR-1, FR-3, FR-4 en FR-5.
"""

import json
import zipfile
from pathlib import Path

import pytest

from bulk_analyser import AnalyseFout, analyseer, genereeer_json, genereeer_markdown


def test_fr1_geldige_openai_export_levert_volledig_rapport(openai_export: Path) -> None:
    rapport = analyseer(openai_export)

    assert rapport.aantal_gesprekken == 2
    assert rapport.aantal_berichten == 2
    assert rapport.aggregaten.totaal.requests == 2
    assert rapport.aggregaten.totaal.energie.laag >= 0.0

    json_text = genereeer_json(rapport)
    markdown = genereeer_markdown(rapport)
    # beide outputs zijn niet leeg en parseerbaar
    assert isinstance(json_text, str) and json.loads(json_text)
    assert isinstance(markdown, str) and markdown.strip()


def test_fr1_identieke_input_geeft_identieke_output(openai_export: Path) -> None:
    eerste = genereeer_json(analyseer(openai_export))
    tweede = genereeer_json(analyseer(openai_export))
    assert eerste == tweede


def test_fr1_zip_levert_hetzelfde_rapport_als_de_map(
    mistral_export: Path, tmp_path: Path
) -> None:
    zip_pad = tmp_path / "chat-export.zip"
    with zipfile.ZipFile(zip_pad, "w") as archief:
        for bestand in mistral_export.rglob("*"):
            if bestand.is_file():
                archief.write(bestand, bestand.relative_to(mistral_export.parent))

    rapport_map = analyseer(mistral_export)
    rapport_zip = analyseer(zip_pad)

    assert genereeer_json(rapport_map) == genereeer_json(rapport_zip)


def test_fr3_json_bevat_alle_rapportvelden(openai_export: Path) -> None:
    rapport = analyseer(openai_export)
    data = json.loads(genereeer_json(rapport))

    verwacht_toplevel = {
        "herkende_aanbieder",
        "herkende_formaat",
        "aantal_gesprekken",
        "aantal_berichten",
        "totaal",
        "per_model",
        "per_maand",
        "per_gesprek",
        "per_provider",
        "overgeslagen",
        "waarschuwingen",
        "methode_en_bronnen",
    }
    assert verwacht_toplevel <= set(data)

    totaal = data["totaal"]
    verwacht_totaal = {
        "tokens",
        "requests",
        "energie",
        "uitstoot",
        "aantal_onbekend_model",
        "aandeel_onbekend_model",
    }
    assert verwacht_totaal <= set(totaal)
    assert set(totaal["energie"]) == {"laag", "hoog", "gemiddelde"}
    assert set(totaal["uitstoot"]) == {"laag", "hoog", "gemiddelde"}


def test_fr3_json_schema_test_elk_aggregaat_veld(openai_export: Path) -> None:
    rapport = analyseer(openai_export)
    data = json.loads(genereeer_json(rapport))

    basis = {"tokens", "requests", "energie", "uitstoot", "aantal_onbekend_model"}

    for maand, aggregaat in data["per_maand"].items():
        assert isinstance(maand, str) and maand
        assert basis <= set(aggregaat)

    for model, aggregaat in data["per_model"].items():
        assert isinstance(model, str) and model
        assert basis <= set(aggregaat)
        assert "provider" in aggregaat

    for _gesprek_id, aggregaat in data["per_gesprek"].items():
        assert basis <= set(aggregaat)
        assert {"gesprek_id", "titel", "provider"} <= set(aggregaat)

    for _provider, aggregaat in data["per_provider"].items():
        assert basis <= set(aggregaat)
        assert "provider" in aggregaat


def test_fr4_markdown_bevat_de_sectie_methode_en_bronnen(openai_export: Path) -> None:
    rapport = analyseer(openai_export)
    markdown = genereeer_markdown(rapport)

    sectie = markdown.lower()
    assert "methode" in sectie
    assert "bronnen" in sectie
    # elke opsomming uit 'Rapport' staat in de markdown
    for woord in (
        "aanbieder",
        "formaat",
        "tokenschatting",
        "ecologits",
        "versie",
        "elektriciteitsmix",
        "zones",
        "bandbreedte",
        "zonder model",
        "overgeslagen",
        "bron",
    ):
        assert woord in sectie, f"ontbrekend onderwerp in 'methode en bronnen': {woord}"


def test_fr5_ontbrekende_map_geeft_duidelijke_fout(tmp_path: Path) -> None:
    ontbrekend = tmp_path / "bestaat-niet"
    with pytest.raises(AnalyseFout) as exc_info:
        analyseer(ontbrekend)

    melding = str(exc_info.value)
    assert exc_info.value.stap == "invoer"
    assert "bestaat-niet" in exc_info.value.oorzaak
    assert "bestaat-niet" in melding


def test_fr5_lege_export_geeft_duidelijke_fout_zonder_crash(tmp_path: Path) -> None:
    leeg = tmp_path / "lege-map"
    leeg.mkdir()
    with pytest.raises(AnalyseFout) as exc_info:
        analyseer(leeg)

    assert exc_info.value.stap in {"invoer", "detectie"}
    assert exc_info.value.oorzaak.strip()


def test_fr5_beschadigde_zip_geeft_duidelijke_fout(tmp_path: Path) -> None:
    zip_pad = tmp_path / "kapot.zip"
    zip_pad.write_bytes(b"dit is geen geldige zip")
    with pytest.raises(AnalyseFout) as exc_info:
        analyseer(zip_pad)

    assert exc_info.value.stap == "invoer"
    assert "kapot.zip" in exc_info.value.oorzaak
