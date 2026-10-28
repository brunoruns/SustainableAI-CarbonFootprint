"""Elektriciteitsmix-zones en de datacenterregio-tabel (FR-5, FR-6, A1, A3).

De configtabel met de bekende datacenterregio per aanbieder staat als data los
van de code (aanname A3) in `data/datacenter_regios.json` en wordt in de ADR
vastgelegd.
"""

import json
from collections.abc import Mapping
from pathlib import Path

from ecologits.electricity_mix_repository import electricity_mixes

from carbon_calculator.fouten import OngeldigeZoneError

DEFAULT_ZONE = "WOR"
_ALTERNATIEVE_ZONE = "EEE"

_ZONE_OPTIES = (DEFAULT_ZONE, _ALTERNATIEVE_ZONE)

_DATA_BESTAND = Path(__file__).resolve().parent / "data" / "datacenter_regios.json"


def zone_codes() -> list[str]:
    """Alle zones die EcoLogits ondersteunt.

    Dit zijn de ISO 3166-1 alpha-3 codes plus `WOR` en `EEE`, zoals de
    bibliotheek die ondersteunt (aanname A1).

    Returns:
        De gesorteerde lijst van zonecodes.
    """
    return sorted(mix.zone for mix in electricity_mixes.list_electricity_mixes())


def valideer_zone(zone: str) -> None:
    """Controleer of EcoLogits de zone kent (FR-5).

    Args:
        zone: de elektriciteitsmix-zone om te controleren.

    Raises:
        OngeldigeZoneError: de zone is niet geregistreerd. De melding noemt de
            zone en geeft geldige voorbeelden.
    """
    if zone in zone_codes():
        return
    raise OngeldigeZoneError(
        f"ongeldige elektriciteitsmix-zone '{zone}'. Gebruik een "
        "ISO 3166-1 alpha-3 code uit de ondersteuning van EcoLogits, of "
        "WOR of EEE (bijvoorbeeld WOR, EEE, NLD, USA of SWE)."
    )


def _laad_datacenter_regios() -> dict[str, dict[str, str]]:
    """Laad de configtabel met datacenterregio's uit de package-data (A3)."""
    data = json.loads(_DATA_BESTAND.read_text(encoding="utf-8"))
    return {
        provider: {"zone": regio["zone"], "bron": regio["bron"]}
        for provider, regio in data["regios"].items()
    }


DATACENTER_REGIOS = _laad_datacenter_regios()


def bepaal_zones(provider: str, zones_per_provider: Mapping[str, str]) -> tuple[str, ...]:
    """Bepaal minstens twee unieke zones voor de bandbreedte (FR-6).

    De primaire zone is de door de gebruiker geconfigureerde zone per provider,
    anders de fallback `WOR` (FR-5). De tweede zone is de datacenterregio uit
    de configtabel (voorkeur 2 uit de spec). Vallen die samen, dan wordt
    `EEE` of `WOR` als alternatief toegevoegd zodat er altijd minstens twee
    unieke zones zijn.

    Args:
        provider: de provider van het gesprek.
        zones_per_provider: de primaire zone per provider uit de config.

    Returns:
        Minstens twee unieke, geldige zonecodes.
    """
    primair = zones_per_provider.get(provider, DEFAULT_ZONE)
    regio = DATACENTER_REGIOS.get(provider, {}).get("zone", DEFAULT_ZONE)
    zones = [primair]
    for kandidaat in (regio, *_ZONE_OPTIES):
        if len(zones) >= 2:
            break
        if kandidaat not in zones:
            zones.append(kandidaat)
    if len(zones) < 2:
        raise OngeldigeZoneError(
            f"kan geen tweede elektriciteitsmix-zone bepalen naast '{primair}' "
            f"voor provider '{provider}'"
        )
    for zone in zones:
        valideer_zone(zone)
    return tuple(zones)
