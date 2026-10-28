"""Tests voor de parsers (FR-2 t/m FR-6) en M1a op de echte mistral-data."""

from pathlib import Path

from structuur_detectie import parseer

_CANONIEKE_GESPREK_VELDEN = frozenset({"id", "titel", "provider", "created_at", "berichten"})
_CANONIEKE_BERICHT_VELDEN = frozenset({"id", "rol", "inhoud", "created_at", "model"})


def test_fr2_openai_levert_uitsluitend_canonieke_gesprekken(openai_export: Path) -> None:
    gesprekken = parseer(openai_export)
    assert len(gesprekken) == 2
    for gesprek in gesprekken:
        assert set(gesprek.naar_dict()) == _CANONIEKE_GESPREK_VELDEN
        assert gesprek.provider == "openai"
        assert gesprek.titel is not None
        for bericht in gesprek.berichten:
            assert set(bericht.naar_dict()) == _CANONIEKE_BERICHT_VELDEN
            assert bericht.rol in {"user", "assistant", "system", "tool"}


def test_fr2_mistral_levert_uitsluitend_canonieke_gesprekken(mistral_export: Path) -> None:
    gesprekken = parseer(mistral_export)
    assert len(gesprekken) == 2
    for gesprek in gesprekken:
        assert set(gesprek.naar_dict()) == _CANONIEKE_GESPREK_VELDEN
        assert gesprek.provider == "mistral"
        assert gesprek.titel is None
        for bericht in gesprek.berichten:
            assert set(bericht.naar_dict()) == _CANONIEKE_BERICHT_VELDEN


def test_fr3_rollen_worden_vertaald_en_delen_samengevoegd(openai_export: Path) -> None:
    gesprek = parseer(openai_export)[0]
    assert {bericht.rol for bericht in gesprek.berichten} == {"system", "user", "assistant", "tool"}
    samengevoegd = next(bericht for bericht in gesprek.berichten if bericht.id == "msg-assistent")
    assert samengevoegd.inhoud == "Natuurlijk. Hier is het antwoord."


def test_fr4_alleen_het_actieve_pad_wordt_opgenomen(openai_export: Path) -> None:
    gesprek = parseer(openai_export)[0]
    ids = [bericht.id for bericht in gesprek.berichten]
    assert "msg-vertakking" not in ids
    assert set(ids) == {
        "msg-systeem",
        "msg-gebruiker",
        "msg-assistent",
        "msg-tool",
        "msg-assistent-2",
    }


def test_fr5_model_komt_uit_model_slug(openai_export: Path) -> None:
    gesprek = parseer(openai_export)[0]
    assistent = next(bericht for bericht in gesprek.berichten if bericht.id == "msg-assistent")
    assert assistent.model == "gpt-4o"
    gebruiker = next(bericht for bericht in gesprek.berichten if bericht.id == "msg-gebruiker")
    assert gebruiker.model is None


def test_fr5_mistral_berichten_krijgen_altijd_model_null(mistral_export: Path) -> None:
    for gesprek in parseer(mistral_export):
        assert all(bericht.model is None for bericht in gesprek.berichten)


def test_fr6_berichten_gesorteerd_met_null_als_laatste_stabiel(openai_export: Path) -> None:
    berichten = parseer(openai_export)[0].berichten
    assert [bericht.created_at for bericht in berichten] == [
        1733294330.0,
        1733294335.0,
        1733294339.5,
        None,
        None,
    ]
    assert [bericht.id for bericht in berichten][-2:] == ["msg-assistent", "msg-tool"]


def test_fr6_mistral_onversorteerde_berichten_worden_gesorteerd(mistral_export: Path) -> None:
    by_id = {gesprek.id: gesprek for gesprek in parseer(mistral_export)}
    gesprek = by_id["aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"]
    assert [bericht.id for bericht in gesprek.berichten] == ["m-1", "m-2", "m-3", "m-4"]
    assert gesprek.berichten[0].created_at == "2024-06-01T10:00:01.000Z"
    assert gesprek.berichten[-1].inhoud == ""
    assert gesprek.created_at == "2024-06-01T10:00:01.000Z"


def test_mistral_gesprek_id_komt_uit_het_bestand(mistral_export: Path) -> None:
    by_id = {gesprek.id: gesprek for gesprek in parseer(mistral_export)}
    assert set(by_id) == {
        "11111111-2222-4333-8444-555555555555",
        "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
    }


def test_mistral_negeert_files_submappen(mistral_export: Path) -> None:
    assert len(parseer(mistral_export)) == 2


def test_openai_gesprek_zonder_actieve_tak_geeft_leeg_gesprek(openai_export: Path) -> None:
    leeg = parseer(openai_export)[1]
    assert leeg.id == "conv-openai-002"
    assert leeg.berichten == []
    assert leeg.created_at == 1733294400.0


def test_m1a_mistral_parsed_de_echte_voorbeelden_uit_context(
    echte_mistral_export: Path,
) -> None:
    verwachte_ids = {
        pad.stem.removeprefix("chat-") for pad in echte_mistral_export.glob("chat-*.json")
    }
    gesprekken = parseer(echte_mistral_export)
    assert len(gesprekken) == len(verwachte_ids)
    assert {gesprek.id for gesprek in gesprekken} == verwachte_ids
    for gesprek in gesprekken:
        assert gesprek.provider == "mistral"
        assert gesprek.titel is None
        assert all(bericht.rol in {"user", "assistant"} for bericht in gesprek.berichten)
        assert all(bericht.model is None for bericht in gesprek.berichten)
        assert all(isinstance(bericht.inhoud, str) for bericht in gesprek.berichten)
        tijden = [
            bericht.created_at for bericht in gesprek.berichten if bericht.created_at is not None
        ]
        assert tijden == sorted(tijden)
