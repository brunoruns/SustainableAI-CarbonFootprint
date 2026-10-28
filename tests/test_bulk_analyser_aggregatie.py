"""Tests voor de aggregatie van de bulk analyser (FR-2 en FR-6).

Deze tests definiëren het publieke contract van `bulk_analyser.aggregeer` en
`bulk_analyser.maand_van`, nog zonder dat de module is geïmplementeerd (spec-first).
"""

from bulk_analyser import aggregeer, maand_van
from carbon_calculator import BerekenConfig, WaardeBereik, bereken_gesprekken
from structuur_detectie import Gesprek


def test_maand_van_epoch_seconde_geeft_utc_maand() -> None:
    # 1704067200 is 2024-01-01T00:00:00Z, 1706745600 is 2024-02-01T00:00:00Z.
    assert maand_van(1704067200.0) == "2024-01"
    assert maand_van(1706745600.0) == "2024-02"


def test_maand_van_iso_met_z_suffix_geeft_utc_maand() -> None:
    assert maand_van("2024-02-01T00:00:01.000Z") == "2024-02"


def test_maand_van_zonder_tijdstip_geeft_geen_maand() -> None:
    assert maand_van(None) is None


def _tel_op(waarden: list[WaardeBereik]) -> WaardeBereik:
    """Tel een reeks bereiken op; een lege lijst geeft een nulbereik."""
    totaal = WaardeBereik(0.0, 0.0, 0.0)
    for waarde in waarden:
        totaal = totaal + waarde
    return totaal


def test_fr2_som_per_model_is_gelijk_aan_totaal(
    gemengde_gesprekken: list[Gesprek], gemengde_config: BerekenConfig
) -> None:
    berekening = bereken_gesprekken(gemengde_gesprekken, gemengde_config)
    aggregaten = aggregeer(gemengde_gesprekken, berekening)

    totaal = aggregaten.totaal
    modellen = list(aggregaten.per_model.values())
    assert modellen

    assert sum(a.tokens for a in modellen) == totaal.tokens
    assert sum(a.requests for a in modellen) == totaal.requests
    assert sum(a.aantal_onbekend_model for a in modellen) == totaal.aantal_onbekend_model

    energie = _tel_op([a.energie for a in modellen])
    uitstoot = _tel_op([a.uitstoot for a in modellen])
    assert energie.laag == totaal.energie.laag
    assert energie.hoog == totaal.energie.hoog
    assert uitstoot.laag == totaal.uitstoot.laag
    assert uitstoot.hoog == totaal.uitstoot.hoog


def test_fr2_som_per_maand_is_gelijk_aan_totaal(
    gemengde_gesprekken: list[Gesprek], gemengde_config: BerekenConfig
) -> None:
    berekening = bereken_gesprekken(gemengde_gesprekken, gemengde_config)
    aggregaten = aggregeer(gemengde_gesprekken, berekening)

    totaal = aggregaten.totaal
    maanden = list(aggregaten.per_maand.values())
    assert maanden

    assert sum(a.requests for a in maanden) == totaal.requests
    assert sum(a.tokens for a in maanden) == totaal.tokens

    energie = _tel_op([a.energie for a in maanden])
    uitstoot = _tel_op([a.uitstoot for a in maanden])
    assert energie.gemiddelde == totaal.energie.gemiddelde
    assert uitstoot.gemiddelde == totaal.uitstoot.gemiddelde


def test_fr2_som_per_gesprek_is_gelijk_aan_totaal(
    gemengde_gesprekken: list[Gesprek], gemengde_config: BerekenConfig
) -> None:
    berekening = bereken_gesprekken(gemengde_gesprekken, gemengde_config)
    aggregaten = aggregeer(gemengde_gesprekken, berekening)

    totaal = aggregaten.totaal
    gesprekken = list(aggregaten.per_gesprek.values())
    assert gesprekken

    assert sum(a.requests for a in gesprekken) == totaal.requests
    assert sum(a.tokens for a in gesprekken) == totaal.tokens
    assert sum(a.aantal_onbekend_model for a in gesprekken) == totaal.aantal_onbekend_model


def test_fr2_som_per_provider_is_gelijk_aan_totaal(
    gemengde_gesprekken: list[Gesprek], gemengde_config: BerekenConfig
) -> None:
    berekening = bereken_gesprekken(gemengde_gesprekken, gemengde_config)
    aggregaten = aggregeer(gemengde_gesprekken, berekening)

    totaal = aggregaten.totaal
    providers = list(aggregaten.per_provider.values())
    assert providers

    assert sum(a.requests for a in providers) == totaal.requests
    assert sum(a.tokens for a in providers) == totaal.tokens


def test_fr6_gemengde_export_groepeert_per_provider(
    gemengde_gesprekken: list[Gesprek], gemengde_config: BerekenConfig
) -> None:
    berekening = bereken_gesprekken(gemengde_gesprekken, gemengde_config)
    aggregaten = aggregeer(gemengde_gesprekken, berekening)

    assert set(aggregaten.per_provider) == {"openai", "mistral"}
    per_naam = {p.provider: p for p in aggregaten.per_provider.values()}
    assert per_naam["openai"].provider == "openai"
    assert per_naam["mistral"].provider == "mistral"


def test_fr6_per_gesprek_vermeldt_provider_en_titel(
    gemengde_gesprekken: list[Gesprek], gemengde_config: BerekenConfig
) -> None:
    berekening = bereken_gesprekken(gemengde_gesprekken, gemengde_config)
    aggregaten = aggregeer(gemengde_gesprekken, berekening)

    openai_gesprek = aggregaten.per_gesprek["conv-openai"]
    assert openai_gesprek.provider == "openai"
    assert openai_gesprek.titel == "OpenAI voorbeeld"

    mistral_gesprek = aggregaten.per_gesprek["conv-mistral"]
    assert mistral_gesprek.provider == "mistral"
    assert mistral_gesprek.titel is None
    assert set(aggregaten.per_gesprek) == {"conv-openai", "conv-mistral"}


def test_fr6_aggregatiestructuur_op_de_schijf(
    gemengde_gesprekken: list[Gesprek], gemengde_config: BerekenConfig
) -> None:
    berekening = bereken_gesprekken(gemengde_gesprekken, gemengde_config)
    aggregaten = aggregeer(gemengde_gesprekken, berekening)

    assert set(aggregaten.per_maand) == {"2024-01", "2024-02"}
    assert set(aggregaten.per_model) >= {"gpt-4o-mini", "onbekend"}
    assert aggregaten.totaal.requests == 2
    assert aggregaten.totaal.tokens > 0
    assert 0.0 <= aggregaten.totaal.aandeel_onbekend_model <= 1.0
