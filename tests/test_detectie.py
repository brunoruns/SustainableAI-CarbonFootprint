"""Tests voor de detector en de registry (FR-1, FR-7 en FR-8)."""

from pathlib import Path

import pytest

from structuur_detectie import (
    Gesprek,
    OnbekendFormaatError,
    ParseFout,
    Parser,
    Registry,
    detecteer,
    parseer,
)


def test_fr1_detectie_openai_zonder_gebruikersinput(openai_export: Path) -> None:
    assert detecteer(openai_export) == "openai"


def test_fr1_detectie_mistral_zonder_gebruikersinput(mistral_export: Path) -> None:
    assert detecteer(mistral_export) == "mistral"


def test_fr1_parseer_geeft_canoniek_model_van_de_juiste_provider(openai_export: Path) -> None:
    gesprekken = parseer(openai_export)
    assert gesprekken[0].provider == "openai"


def test_fr7_nieuwe_parser_wordt_gevonden_en_gebruikt(tmp_path: Path) -> None:
    bestand = tmp_path / "speciale_export.json"
    bestand.write_text('{"bron": "speciaal"}', encoding="utf-8")

    def scoort(bron: Path) -> float:
        return 100.0 if bron.name == "speciale_export.json" else 0.0

    def parse(bron: Path) -> list[Gesprek]:
        return [
            Gesprek(id="spec-1", titel=None, provider="speciaal", created_at=None, berichten=[])
        ]

    registry = Registry()
    registry.registreer(Parser(provider="speciaal", naam="speciaal", scoort=scoort, parse=parse))

    assert registry.detecteer(bestand) == "speciaal"
    assert registry.parseer(bestand)[0].provider == "speciaal"


def test_fr1_eerste_parser_die_succesvol_parseert_wint(tmp_path: Path) -> None:
    bestand = tmp_path / "races.json"
    bestand.write_text('{"races": ["x"]}', encoding="utf-8")

    def scoort_hoog(bron: Path) -> float:
        return 50.0

    def scoort_laag(bron: Path) -> float:
        return 10.0

    def parse_mislukt(bron: Path) -> list[Gesprek]:
        raise ParseFout("past niet bij dit formaat")

    def parse_werkt(bron: Path) -> list[Gesprek]:
        return [Gesprek(id="w-1", titel=None, provider="werkt", created_at=None, berichten=[])]

    registry = Registry()
    registry.registreer(
        Parser(provider="mislukt", naam="mislukt", scoort=scoort_hoog, parse=parse_mislukt)
    )
    registry.registreer(
        Parser(provider="werkt", naam="werkt", scoort=scoort_laag, parse=parse_werkt)
    )

    assert registry.detecteer(bestand) == "werkt"


def test_fr8_onbekende_input_noemt_bestandsnamen_en_json_sleutels(onbekend_export: Path) -> None:
    with pytest.raises(OnbekendFormaatError) as exc_info:
        parseer(onbekend_export)
    melding = str(exc_info.value)
    assert "onbekend_export.json" in melding
    assert "medewerkers" in melding
    assert exc_info.value.json_sleutels == ["medewerkers"]


def test_fr8_misleidende_export_die_parse_faalt_geeft_fout(misleidend_export: Path) -> None:
    with pytest.raises(OnbekendFormaatError) as exc_info:
        parseer(misleidend_export)
    melding = str(exc_info.value)
    assert "chat-export-999" in melding
    assert "chat-vals.json" in melding
    assert "onzin" in melding


def test_fr8_ontbrekend_pad_geeft_duidelijke_fout(tmp_path: Path) -> None:
    ontbrekend = tmp_path / "bestaat-niet"
    with pytest.raises(OnbekendFormaatError) as exc_info:
        parseer(ontbrekend)
    assert "bestaat-niet" in str(exc_info.value)
