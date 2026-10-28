"""Tests voor de modelattributie (FR-2)."""

from carbon_calculator import BerekenConfig, bepaal_model
from carbon_calculator.modellen import ONBEKEND_MODEL
from structuur_detectie import Bericht, Gesprek


def _assistant(model: str | None) -> Bericht:
    return Bericht(
        id="m2",
        rol="assistant",
        inhoud="Hier is een antwoord met voldoende inhoud om te gaan rekenen.",
        created_at=None,
        model=model,
    )


def _gesprek(bericht: Bericht, provider: str = "openai") -> Gesprek:
    return Gesprek(
        id="conv-1",
        titel=None,
        provider=provider,
        created_at=None,
        berichten=[_assistant(None), bericht],
    )


def test_fr2_openai_model_slug_wordt_overgenomen() -> None:
    gesprek = _gesprek(_assistant("gpt-4o"))
    config = BerekenConfig()
    assert bepaal_model(_assistant("gpt-4o"), gesprek, config) == "gpt-4o"


def test_fr2_default_model_slug_van_het_gesprek_wordt_gebruikt() -> None:
    gesprek = _gesprek(_assistant(None))
    config = BerekenConfig(gesprek_standaard_modellen={"conv-1": "gpt-4o-mini"})
    assert bepaal_model(_assistant(None), gesprek, config) == "gpt-4o-mini"


def test_fr2_zonder_model_info_is_onbekend() -> None:
    gesprek = _gesprek(_assistant(None))
    config = BerekenConfig()
    assert bepaal_model(_assistant(None), gesprek, config) == ONBEKEND_MODEL


def test_fr2_mistral_is_altijd_onbekend() -> None:
    gesprek = _gesprek(_assistant(None), provider="mistral")
    config = BerekenConfig(provider_standaard_modellen={"mistral": "mistral-large-2512"})
    # de attributie blijft 'onbekend'; de provider-default geldt pas in de berekening (FR-7).
    assert bepaal_model(_assistant(None), gesprek, config) == ONBEKEND_MODEL


def test_fr2_elk_assistant_bericht_heeft_precies_een_modelwaarde(
    calculator_gesprek: Gesprek,
) -> None:
    config = BerekenConfig(gesprek_standaard_modellen={"conv-1": "gpt-4o-mini"})
    for bericht in calculator_gesprek.berichten:
        if bericht.rol != "assistant":
            continue
        waarde = bepaal_model(bericht, calculator_gesprek, config)
        assert isinstance(waarde, str) and waarde
