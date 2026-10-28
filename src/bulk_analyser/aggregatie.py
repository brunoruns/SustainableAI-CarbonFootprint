"""Aggregatie van de bulk analyser (stap 6 uit de spec).

Berekent de totalen per model, per maand (UTC), per gesprek, per provider en
het algemene totaal uit het berekeningsrapport van module 2. De deelgroepen
tellen op tot het totaal (FR-2).
"""

import datetime

from bulk_analyser.modellen import Aggregaat, AggregatieRapport
from carbon_calculator import (
    ONBEKEND_MODEL,
    BerekeningRapport,
    GesprekBerekening,
    WaardeBereik,
)
from structuur_detectie import Gesprek

_NUL = WaardeBereik(0.0, 0.0, 0.0)

_ISO_UTC_SUFFIXEN = ("Z", "z")


def maand_van(tijdstip: float | str | None) -> str | None:
    """Bepaal de maand (UTC, 'YYYY-MM') van een tijdstip (aanname A2).

    Args:
        tijdstip: epoch-seconden, een ISO 8601-tekst of None.

    Returns:
        De maand in UTC als 'YYYY-MM', of None als het tijdstip ontbreekt of
        niet te lezen is.
    """
    if tijdstip is None:
        return None
    if isinstance(tijdstip, (int, float)):
        ogenblik = datetime.datetime.fromtimestamp(
            float(tijdstip), tz=datetime.UTC
        )
        return ogenblik.strftime("%Y-%m")
    elif isinstance(tijdstip, str):
        ogenblik_iso = _iso_naar_utc(tijdstip)
        if ogenblik_iso is None:
            return None
        return ogenblik_iso.strftime("%Y-%m")
    return None


def _iso_naar_utc(waarde: str) -> datetime.datetime | None:
    """Zet een ISO 8601-tekst om naar een tijdzone-bewuste UTC-tijd.

    Args:
        waarde: een ISO 8601-tekst, eventueel met 'Z'-suffix.

    Returns:
        De tijd in UTC, of None als de tekst niet te lezen is.
    """
    tekst = waarde
    if tekst.endswith(_ISO_UTC_SUFFIXEN):
        tekst = tekst[:-1] + "+00:00"
    try:
        ogenblik = datetime.datetime.fromisoformat(tekst)
    except ValueError:
        return None
    if ogenblik.tzinfo is None:
        ogenblik = ogenblik.replace(tzinfo=datetime.UTC)
    return ogenblik.astimezone(datetime.UTC)


class _Teller:
    """Telhulp om berichten per deelgroep op te sommen (FR-2)."""

    __slots__ = (
        "tokens",
        "requests",
        "energie",
        "uitstoot",
        "aantal_onbekend_model",
    )

    def __init__(self) -> None:
        self.tokens = 0
        self.requests = 0
        self.energie = _NUL
        self.uitstoot = _NUL
        self.aantal_onbekend_model = 0

    def voeg_toe(
        self,
        tokens: int,
        energie: WaardeBereik,
        uitstoot: WaardeBereik,
        onbekend: bool,
    ) -> None:
        """Tel één assistant-bericht op bij deze groep."""
        self.tokens += tokens
        self.requests += 1
        self.energie = self.energie + energie
        self.uitstoot = self.uitstoot + uitstoot
        if onbekend:
            self.aantal_onbekend_model += 1

    def naar_aggregaat(
        self,
        *,
        provider: str | None = None,
        titel: str | None = None,
        gesprek_id: str | None = None,
    ) -> Aggregaat:
        """Bouw een onveranderlijk aggregaat uit de tellerstand."""
        aandeel = (
            self.aantal_onbekend_model / self.requests if self.requests else 0.0
        )
        return Aggregaat(
            tokens=self.tokens,
            requests=self.requests,
            energie=self.energie,
            uitstoot=self.uitstoot,
            aantal_onbekend_model=self.aantal_onbekend_model,
            aandeel_onbekend_model=aandeel,
            provider=provider,
            titel=titel,
            gesprek_id=gesprek_id,
        )


def aggregeer(
    gesprekken: list[Gesprek], berekening: BerekeningRapport
) -> AggregatieRapport:
    """Sommen de per-bericht-berekeningen op tot de aggregaten uit de spec.

    Args:
        gesprekken: de gesprekken uit het canonieke model.
        berekening: het berekeningsrapport van de calculator (module 2).

    Returns:
        Het aggregaatrapport per model, per maand, per gesprek en per provider,
        plus het algemene totaal.
    """
    totaal = _Teller()
    per_model: dict[str, _Teller] = {}
    per_model_providers: dict[str, set[str]] = {}
    per_maand: dict[str, _Teller] = {}
    per_gesprek: dict[str, _Teller] = {}
    per_provider: dict[str, _Teller] = {}

    per_id: dict[str, GesprekBerekening] = {
        berekening_gesprek.gesprek_id: berekening_gesprek
        for berekening_gesprek in berekening.gesprekken
    }
    for gesprek in gesprekken:
        berekening_gesprek = per_id.get(gesprek.id)
        if berekening_gesprek is None:
            continue
        assistant_berichten = [
            bericht for bericht in gesprek.berichten if bericht.rol == "assistant"
        ]
        for canoniek, berekend in zip(
            assistant_berichten, berekening_gesprek.berichten, strict=True
        ):
            energie = berekend.energie if berekend.energie is not None else _NUL
            uitstoot = berekend.uitstoot if berekend.uitstoot is not None else _NUL
            onbekend = berekend.attributie == ONBEKEND_MODEL
            totaal.voeg_toe(berekend.tokens, energie, uitstoot, onbekend)
            per_model.setdefault(berekend.attributie, _Teller()).voeg_toe(
                berekend.tokens, energie, uitstoot, onbekend
            )
            per_model_providers.setdefault(berekend.attributie, set()).add(
                gesprek.provider
            )
            maand = maand_van(canoniek.created_at)
            if maand is not None:
                per_maand.setdefault(maand, _Teller()).voeg_toe(
                    berekend.tokens, energie, uitstoot, onbekend
                )
            per_gesprek.setdefault(gesprek.id, _Teller()).voeg_toe(
                berekend.tokens, energie, uitstoot, onbekend
            )
            per_provider.setdefault(gesprek.provider, _Teller()).voeg_toe(
                berekend.tokens, energie, uitstoot, onbekend
            )

    per_model_uit = {
        naam: teller.naar_aggregaat(
            provider=", ".join(sorted(per_model_providers[naam]))
        )
        for naam, teller in per_model.items()
    }
    per_gesprek_uit = {
        gesprek.id: per_gesprek[gesprek.id].naar_aggregaat(
            provider=gesprek.provider, titel=gesprek.titel, gesprek_id=gesprek.id
        )
        for gesprek in gesprekken
        if gesprek.id in per_gesprek
    }
    per_provider_uit = {
        provider: teller.naar_aggregaat(provider=provider)
        for provider, teller in per_provider.items()
    }
    per_maand_uit = {
        maand: teller.naar_aggregaat() for maand, teller in per_maand.items()
    }
    return AggregatieRapport(
        totaal=totaal.naar_aggregaat(),
        per_model=per_model_uit,
        per_maand=per_maand_uit,
        per_gesprek=per_gesprek_uit,
        per_provider=per_provider_uit,
    )
