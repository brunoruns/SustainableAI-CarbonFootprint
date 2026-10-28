"""Koppeling met de rekenkern EcoLogits (FR-3).

Alle energie- en emissiewaarden komen uit EcoLogits, via `llm_impacts` uit
`ecologits.tracers.utils`. Dat is dezelfde high-level functie die de officiële
EcoLogits-API intern gebruikt voor `POST /v1/estimations`, zie
`docs/ADR/carbon-calculator.md`. Deze module bevat geen eigen energie- of
uitstootlogica.
"""

import math
from dataclasses import dataclass
from typing import Any

from ecologits.tracers.utils import llm_impacts

from carbon_calculator.fouten import (
    EcoLogitsFout,
    ModelOnbekendBijEcoLogits,
    OngeldigeProviderError,
    OngeldigeZoneError,
)
from carbon_calculator.numeriek import WaardeBereik

_PROVIDER_NAAM = {"openai": "openai", "mistral": "mistralai"}


def _ecologits_provider(provider: str) -> str:
    """Vertaal de provider naar de naam die EcoLogits gebruikt.

    EcoLogits gebruikt `mistralai` waar de exportsprovider `mistral` heet.

    Args:
        provider: de provider uit het canonieke model.

    Returns:
        De providernaam zoals EcoLogits die kent.

    Raises:
        OngeldigeProviderError: de provider wordt in v1 niet ondersteund.
    """
    if provider not in _PROVIDER_NAAM:
        raise OngeldigeProviderError(
            f"provider '{provider}' wordt door de calculator niet ondersteund; "
            "v1 ondersteunt alleen 'openai' en 'mistral'."
        )
    return _PROVIDER_NAAM[provider]


@dataclass(frozen=True)
class EcoUitkomst:
    """De impact zoals EcoLogits die voor één zone berekent."""

    zone: str
    energie: WaardeBereik
    uitstoot: WaardeBereik
    waarschuwingen: tuple[str, ...]


def _als_bereik(waarde: Any) -> WaardeBereik:
    """Zet een waarde uit EcoLogits om naar een `WaardeBereik`.

    EcoLogits geeft voor sommige modellen een vaste waarde (float) in plaats
    van een `RangeValue`; dan is laag gelijk aan hoog.

    Args:
        waarde: een value-veld uit het ImpactsOutput-object.

    Returns:
        Een WaardeBereik met laag, hoog en gemiddelde.
    """
    if isinstance(waarde, (float, int)):
        waarde_float = float(waarde)
        return WaardeBereik(
            laag=waarde_float, hoog=waarde_float, gemiddelde=waarde_float
        )
    return WaardeBereik(
        laag=waarde.min, hoog=waarde.max, gemiddelde=waarde.mean
    )


def _verwerk_ecologits_fouten(
    fouten: Any, model: str, provider: str, zone: str
) -> None:
    """Vertaal de fouten die EcoLogits in het resultaat meldt naar exceptions.

    Args:
        fouten: de `errors` uit het ImpactsOutput-object van EcoLogits.
        model: de gevraagde modelnaam (voor de melding).
        provider: de gevraagde provider (voor de melding).
        zone: de gevraagde elektriciteitsmix-zone (voor de melding).

    Raises:
        OngeldigeZoneError: een zone-not-registered fout van EcoLogits.
        ModelOnbekendBijEcoLogits: een model-not-registered fout van EcoLogits.
        EcoLogitsFout: een onverwachte fout van EcoLogits.
    """
    codes = [str(fout.code) for fout in fouten]
    if "zone-not-registered" in codes:
        raise OngeldigeZoneError(
            f"de elektriciteitsmix-zone '{zone}' wordt niet door EcoLogits "
            f"ondersteund voor provider '{provider}'. Gebruik een "
            "ISO 3166-1 alpha-3 code, WOR of EEE."
        )
    if "model-not-registered" in codes:
        raise ModelOnbekendBijEcoLogits(
            f"model '{model}' is niet in de ecologits-modelgegevens voor "
            f"provider '{provider}' geregistreerd."
        )
    raise EcoLogitsFout(
        f"EcoLogits gaf een onverwachte fout terug: {', '.join(codes)}"
    )


def schat_impact(
    provider: str,
    model: str,
    output_token_count: int,
    zone: str,
    request_latency: float | None = None,
) -> EcoUitkomst:
    """Vraag de impact van één request aan EcoLogits (FR-3).

    Alle energie- en emissiecijfers komen hier vandaan; de module rekent zelf
    niets na.

    Args:
        provider: "openai" of "mistral".
        model: de modelnaam zoals EcoLogits die kent.
        output_token_count: het aantal output-tokens van het bericht.
        zone: de elektriciteitsmix-zone (ISO 3166-1 alpha-3, WOR of EEE).
        request_latency: de gemeten latency in seconden. `None` betekent dat er
            geen latency is gemeten; dan gebruikt EcoLogits `oneindig` als
            vaste default (A4) en daalt de nauwkeurigheid van de schatting.

    Returns:
        De energie- en uitstootwaarden voor deze zone.

    Raises:
        OngeldigeProviderError: de provider wordt niet ondersteund.
        OngeldigeZoneError: de zone is niet door EcoLogits geregistreerd.
        ModelOnbekendBijEcoLogits: het model is niet geregistreerd.
        EcoLogitsFout: een onverwachte fout van EcoLogits.
    """
    latency = request_latency if request_latency is not None else math.inf
    uitkomst = llm_impacts(
        provider=_ecologits_provider(provider),
        model_name=model,
        output_token_count=output_token_count,
        request_latency=latency,
        electricity_mix_zone=zone,
    )
    if uitkomst.errors:
        _verwerk_ecologits_fouten(uitkomst.errors, model, provider, zone)
    assert uitkomst.energy is not None, "ecologits gaf geen energy terug"
    assert uitkomst.gwp is not None, "ecologits gaf geen gwp terug"
    return EcoUitkomst(
        zone=zone,
        energie=_als_bereik(uitkomst.energy.value),
        uitstoot=_als_bereik(uitkomst.gwp.value),
        waarschuwingen=tuple(
            f"{waarschuwing.code}: {waarschuwing.message}"
            for waarschuwing in (uitkomst.warnings or [])
        ),
    )
