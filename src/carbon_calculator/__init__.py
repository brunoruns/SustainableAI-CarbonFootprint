"""Module 2: carbon calculator voor chat exports.

Volgt `specs/spec_carbon_calculator.md`: per assistant-bericht de geschatte
energie (kWh) en uitstoot (kg CO2eq) berekenen met EcoLogits als rekenkern.
"""

from carbon_calculator.berekening import (
    BerekeningRapport,
    BerichtBerekening,
    GesprekBerekening,
    ZoneUitkomst,
    bereken_gesprek,
    bereken_gesprekken,
)
from carbon_calculator.config import STANDAARD_PROVIDER_MODELLEN, BerekenConfig
from carbon_calculator.ecologits_koppeling import schat_impact
from carbon_calculator.fouten import (
    EcoLogitsFout,
    ModelOnbekendBijEcoLogits,
    OngeldigeProviderError,
    OngeldigeZoneError,
)
from carbon_calculator.modellen import ONBEKEND_MODEL, bepaal_model
from carbon_calculator.numeriek import WaardeBereik
from carbon_calculator.tokens import is_niet_westers, schat_tokens

__all__ = [
    "BerekenConfig",
    "BerekeningRapport",
    "BerichtBerekening",
    "EcoLogitsFout",
    "GesprekBerekening",
    "ModelOnbekendBijEcoLogits",
    "ONBEKEND_MODEL",
    "OngeldigeProviderError",
    "OngeldigeZoneError",
    "STANDAARD_PROVIDER_MODELLEN",
    "WaardeBereik",
    "ZoneUitkomst",
    "bepaal_model",
    "bereken_gesprek",
    "bereken_gesprekken",
    "is_niet_westers",
    "schat_impact",
    "schat_tokens",
]
