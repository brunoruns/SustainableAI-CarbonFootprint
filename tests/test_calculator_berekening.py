"""Tests voor de EcoLogits-integratie en de berekening (FR-3 t/m FR-7)."""

import math
from typing import Any, cast

import pytest
from ecologits.tracers.utils import llm_impacts

from carbon_calculator import (
    STANDAARD_PROVIDER_MODELLEN,
    BerekenConfig,
    OngeldigeProviderError,
    OngeldigeZoneError,
    WaardeBereik,
    bereken_gesprek,
    bereken_gesprekken,
    schat_impact,
)
from carbon_calculator.modellen import ONBEKEND_MODEL
from structuur_detectie import Bericht, Gesprek


def _assistant(inhoud: str, model: str | None, bericht_id: str = "m2") -> Bericht:
    return Bericht(
        id=bericht_id,
        rol="assistant",
        inhoud=inhoud,
        created_at=None,
        model=model,
    )


def _openai_gesprek(*berichten: Bericht) -> Gesprek:
    return Gesprek(
        id="conv-1",
        titel="Voorbeeld",
        provider="openai",
        created_at=None,
        berichten=list(berichten),
    )


def test_fr3_waarden_komen_uit_ecologits_zelf() -> None:
    uit = schat_impact("openai", "gpt-4o-mini", 100, "WOR")
    verwacht = llm_impacts(
        provider="openai",
        model_name="gpt-4o-mini",
        output_token_count=100,
        request_latency=math.inf,
        electricity_mix_zone="WOR",
    )
    assert verwacht.energy is not None
    assert verwacht.gwp is not None
    energie_waarde = cast(Any, verwacht.energy.value)
    uitstoot_waarde = cast(Any, verwacht.gwp.value)
    for waarde, rangevalue in (
        (uit.energie.laag, energie_waarde.min),
        (uit.energie.hoog, energie_waarde.max),
        (uit.energie.gemiddelde, energie_waarde.mean),
    ):
        assert waarde == pytest.approx(rangevalue)
    for waarde, rangevalue in (
        (uit.uitstoot.laag, uitstoot_waarde.min),
        (uit.uitstoot.hoog, uitstoot_waarde.max),
        (uit.uitstoot.gemiddelde, uitstoot_waarde.mean),
    ):
        assert waarde == pytest.approx(rangevalue)


def test_fr4_alle_velden_aanwezig_en_reproduceerbaar(calculator_gesprek: Gesprek) -> None:
    config = BerekenConfig()
    eerste = bereken_gesprek(calculator_gesprek, config)
    tweede = bereken_gesprek(calculator_gesprek, config)
    bericht = eerste.berichten[0]
    assert bericht.energie is not None
    assert bericht.uitstoot is not None
    assert bericht.energie.laag <= bericht.energie.gemiddelde <= bericht.energie.hoog
    assert bericht.uitstoot.laag <= bericht.uitstoot.gemiddelde <= bericht.uitstoot.hoog
    assert bericht.zones
    assert bericht.versie_modelgegevens
    assert bericht.tokens == len(calculator_gesprek.berichten[1].inhoud) // 4
    assert tweede == eerste


def test_fr5_ongeldige_zone_geeft_een_duidelijke_fout() -> None:
    with pytest.raises(OngeldigeZoneError) as exc_info:
        schat_impact("openai", "gpt-4o-mini", 100, "XYZ")
    melding = str(exc_info.value)
    assert "XYZ" in melding
    assert "WOR" in melding


def test_fr5_niet_configureerbare_zone_wordt_voor_de_berekening_afgewezen(
    calculator_gesprek: Gesprek,
) -> None:
    config = BerekenConfig(zones_per_provider={"openai": "XYZ"})
    with pytest.raises(OngeldigeZoneError):
        bereken_gesprek(calculator_gesprek, config)


def test_fr6_minstens_twee_zones_en_laag_hoog_range(
    calculator_gesprek: Gesprek,
) -> None:
    berekening = bereken_gesprek(calculator_gesprek, BerekenConfig())
    bericht = berekening.berichten[0]
    assert len(bericht.zones) >= 2
    assert bericht.uitkomsten_per_zone
    assert bericht.energie is not None
    uitkomsten = [zone.energie.gemiddelde for zone in bericht.uitkomsten_per_zone]
    assert bericht.zones == tuple(zone.zone for zone in bericht.uitkomsten_per_zone)
    assert bericht.energie.laag == pytest.approx(min(uitkomsten))
    assert bericht.energie.hoog == pytest.approx(max(uitkomsten))
    assert min(uitkomsten) <= bericht.energie.laag <= max(uitkomsten)
    assert min(uitkomsten) <= bericht.energie.hoog <= max(uitkomsten)


def test_fr6_range_bevat_beide_zone_uitkomsten(calculator_gesprek: Gesprek) -> None:
    bericht = bereken_gesprek(calculator_gesprek, BerekenConfig()).berichten[0]
    assert bericht.uitstoot is not None
    # de datacenterregio uit de configtabel geeft een andere uitkomst dan WOR
    uitkomsten = [zone.uitstoot.gemiddelde for zone in bericht.uitkomsten_per_zone]
    assert len(set(uitkomsten)) >= 2
    assert bericht.uitstoot.gemiddelde == pytest.approx(
        sum(uitkomsten) / len(uitkomsten)
    )


def test_fr6_zone_gelijk_aan_datacenterregio_levert_toch_twee_zones(
    calculator_gesprek: Gesprek,
) -> None:
    # de geconfigureerde zone valt samen met de regio uit de configtabel
    config = BerekenConfig(zones_per_provider={"openai": "USA"})
    bericht = bereken_gesprek(calculator_gesprek, config).berichten[0]
    assert len(bericht.zones) >= 2
    assert len(set(bericht.zones)) == len(bericht.zones)
    assert len(bericht.zones) == len(bericht.uitkomsten_per_zone)


def test_fr7_mistral_krijgt_standaard_een_basismodel() -> None:
    bericht = _assistant("Een antwoord met voldoende inhoud om te berekenen.", None)
    mistral = Gesprek(
        id="conv-m",
        titel=None,
        provider="mistral",
        created_at=None,
        berichten=[bericht],
    )
    gesprek = bereken_gesprek(mistral, BerekenConfig())
    resultaat = gesprek.berichten[0]
    assert resultaat.attributie == ONBEKEND_MODEL
    assert resultaat.overgeslagen is False
    assert resultaat.model == STANDAARD_PROVIDER_MODELLEN["mistral"]
    assert any("standaard-basismodel" in w for w in resultaat.waarschuwingen)
    rapport = bereken_gesprekken([mistral], BerekenConfig())
    assert rapport.aantal_overgeslagen == 0
    assert rapport.aantal_onbekend_model == 1


def test_fr7_openai_onbekend_zonder_fallback_wordt_overgeslagen() -> None:
    bericht = _assistant("Een antwoord met voldoende inhoud om te berekenen.", None)
    gesprek = _openai_gesprek(bericht)
    resultaat = bereken_gesprek(gesprek, BerekenConfig()).berichten[0]
    assert resultaat.attributie == ONBEKEND_MODEL
    assert resultaat.overgeslagen is True
    assert resultaat.model is None
    assert "fallback" in (resultaat.reden or "")
    rapport = bereken_gesprekken([_openai_gesprek(bericht)], BerekenConfig())
    assert rapport.aantal_overgeslagen == 1


def test_fr7_expliciet_model_overschrijft_het_standaard_basismodel() -> None:
    bericht = _assistant("Een antwoord met voldoende inhoud om te berekenen.", None)
    mistral = Gesprek(
        id="conv-m",
        titel=None,
        provider="mistral",
        created_at=None,
        berichten=[bericht],
    )
    config = BerekenConfig(fallback_model="mistral-small-latest")
    resultaat = bereken_gesprek(mistral, config).berichten[0]
    assert not resultaat.overgeslagen
    assert resultaat.model == "mistral-small-latest"
    assert any("fallback-model" in w for w in resultaat.waarschuwingen)


def test_fr7_zonder_fallback_wijkt_de_totaalsom_niet_uit() -> None:
    gemodeld = _assistant(
        "A clear description of the process and the expected outcome today.",
        "gpt-4o-mini",
        bericht_id="m1",
    )
    onbekend = _assistant("Een tweede antwoord zonder modelinformatie.", None)
    gesprek = _openai_gesprek(gemodeld, onbekend)
    rapport = bereken_gesprekken([gesprek], BerekenConfig())
    assert rapport.aantal_overgeslagen == 1
    meetellende_bereiken = [
        b.energie
        for g in rapport.gesprekken
        for b in g.berichten
        if b.energie is not None
    ]
    assert len(meetellende_bereiken) == 1
    gesommeerd = WaardeBereik(
        laag=sum(b.laag for b in meetellende_bereiken),
        hoog=sum(b.hoog for b in meetellende_bereiken),
        gemiddelde=sum(b.gemiddelde for b in meetellende_bereiken),
    )
    assert gesommeerd == rapport.totale_energie
    assert gesommeerd.laag > 0.0


def test_fr7_provider_default_laat_onbekende_modellen_meetellen() -> None:
    bericht = _assistant("Een antwoord met voldoende inhoud om te berekenen.", None)
    mistral = Gesprek(
        id="conv-m",
        titel=None,
        provider="mistral",
        created_at=None,
        berichten=[bericht],
    )
    config = BerekenConfig(provider_standaard_modellen={"mistral": "mistral-large-2512"})
    gesprek = bereken_gesprek(mistral, config)
    resultaat = gesprek.berichten[0]
    assert not resultaat.overgeslagen
    assert resultaat.model == "mistral-large-2512"
    assert any("mistral-large-2512" in w for w in resultaat.waarschuwingen)


def test_fr7_fallback_model_laat_onbekende_modellen_meetellen() -> None:
    bericht = _assistant("Een antwoord met voldoende inhoud om te berekenen.", None)
    gesprek = _openai_gesprek(bericht)
    config = BerekenConfig(fallback_model="gpt-4o-mini")
    resultaat = bereken_gesprek(gesprek, config).berichten[0]
    assert not resultaat.overgeslagen
    assert resultaat.model == "gpt-4o-mini"
    assert any("gpt-4o-mini" in w for w in resultaat.waarschuwingen)


def test_fr7_model_niet_in_ecologits_wordt_overgeslagen() -> None:
    bericht = _assistant("Een antwoord met voldoende inhoud om te berekenen.", "gpt-2")
    gesprek = _openai_gesprek(bericht)
    config = BerekenConfig()
    resultaat = bereken_gesprek(gesprek, config).berichten[0]
    assert resultaat.overgeslagen is True
    assert "ecologits" in (resultaat.reden or "")


def test_fr8_markering_staat_per_bericht_in_de_uitvoer() -> None:
    westers = _assistant("A normal western text about the weather today.", "gpt-4o-mini")
    oosters = _assistant(
        "你好，世界！今天的天气很好，所以我们决定去公园散步。",
        "gpt-4o-mini",
        bericht_id="m3",
    )
    gesprek = _openai_gesprek(westers, oosters)
    berekening = bereken_gesprek(gesprek, BerekenConfig())
    per_id = {b.bericht_id: b for b in berekening.berichten}
    assert per_id["m2"].niet_westers is False
    assert per_id["m3"].niet_westers is True
    assert berekening.aantal_niet_westers == 1


def test_ongeldige_provider_geeft_duidelijke_fout() -> None:
    claude = Gesprek(
        id="conv-c",
        titel=None,
        provider="claude",
        created_at=None,
        berichten=[_assistant("Een antwoord zonder meer.", "gpt-4o-mini")],
    )
    with pytest.raises(OngeldigeProviderError) as exc_info:
        bereken_gesprek(claude, BerekenConfig())
    assert "claude" in str(exc_info.value)


def test_leeg_rapport_levert_nul_totalen() -> None:
    rapport = bereken_gesprekken([], BerekenConfig())
    assert rapport.aantal_berichten == 0
    assert rapport.aantal_overgeslagen == 0
    assert rapport.totale_energie == WaardeBereik(0.0, 0.0, 0.0)
