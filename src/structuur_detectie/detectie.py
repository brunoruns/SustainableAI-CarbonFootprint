"""Registry en detector: kies de best passende parser voor een export."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from operator import itemgetter
from pathlib import Path

from structuur_detectie.canoniek import Gesprek
from structuur_detectie.fouten import OnbekendFormaatError, ParseFout
from structuur_detectie.parsers import (
    parse_mistral_export,
    parse_openai_export,
    score_mistral,
    score_openai,
)

_MAX_JSON_BESTANDEN = 20


@dataclass(frozen=True)
class Parser:
    """Een parser voor één exportformaat van één provider."""

    provider: str
    naam: str
    scoort: Callable[[Path], float]
    parse: Callable[[Path], list[Gesprek]]


class Registry:
    """Verzameling parsers en de detectie om de juiste te kiezen."""

    def __init__(self) -> None:
        self._parsers: list[Parser] = []

    def registreer(self, parser: Parser) -> None:
        """Voeg een parser toe; dit is het extensiepunt uit FR-7."""
        self._parsers.append(parser)

    def detecteer(self, bron: str | Path) -> str:
        """Detecteer de provider van een export zonder gebruikersinput."""
        parser, _ = self._detecteer_en_parse(bron)
        return parser.provider

    def parseer(self, bron: str | Path) -> list[Gesprek]:
        """Parse een export naar het canonieke model."""
        _, gesprekken = self._detecteer_en_parse(bron)
        return gesprekken

    def analyseer_bron(self, bron: str | Path) -> tuple[str, str, list[Gesprek]]:
        """Detecteer en parse in één gang (voor de bulk-pijplijn).

        Args:
            bron: een map of bestand van een export.

        Returns:
            Een tuple met de aanbieder, de formatnaam en de gesprekken,
            zodat de pijplijn geen tweede detectie hoeft te draaien.
        """
        parser, gesprekken = self._detecteer_en_parse(bron)
        return parser.provider, parser.naam, gesprekken

    def _detecteer_en_parse(self, bron: str | Path) -> tuple[Parser, list[Gesprek]]:
        """Probeer de kandidaten op score; de eerste die parseert wint."""
        pad = Path(bron)
        if not pad.exists():
            raise OnbekendFormaatError(
                f"export niet gevonden op '{pad}'; controleer het pad.",
                bestandsnamen=[],
                json_sleutels=[],
            )
        kandidaten = [(parser.scoort(pad), parser) for parser in self._parsers]
        kandidaten = [paar for paar in kandidaten if paar[0] > 0]
        kandidaten.sort(key=itemgetter(0), reverse=True)
        for _, parser in kandidaten:
            try:
                gesprekken = parser.parse(pad)
            except ParseFout:
                continue
            return parser, gesprekken
        bestandsnamen, json_sleutels = _verzamel_kenmerken(pad)
        raise OnbekendFormaatError(
            f"geen gekend formaat herkend voor '{pad}'.\n"
            f"Gevonden bestanden: {', '.join(bestandsnamen) or 'geen'}.\n"
            f"Gevonden JSON-sleutels: {', '.join(json_sleutels) or 'geen'}.\n"
            "Suggesties: gebruik een OpenAI-export (conversations.json) of "
            "een Mistral-export (map chat-export-... met chat-*.json).",
            bestandsnamen=bestandsnamen,
            json_sleutels=json_sleutels,
        )


def _top_level_sleutels(pad: Path) -> set[str]:
    """Geef de top-level sleutels van een JSON-bestand."""
    try:
        with pad.open(encoding="utf-8") as bestand:
            data = json.load(bestand)
    except (OSError, json.JSONDecodeError):
        return set()
    if isinstance(data, dict):
        return set(data)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return set(data[0])
    return set()


def _verzamel_kenmerken(bron: Path) -> tuple[list[str], list[str]]:
    """Verzamel bestandsnamen en JSON-sleutels voor de foutmelding (FR-8)."""
    bestanden = [bron] if bron.is_file() else sorted(bron.glob("*.json"))[:_MAX_JSON_BESTANDEN]
    bestandsnamen = sorted({bestand.name for bestand in bestanden})
    if bron.is_dir():
        bestandsnamen.insert(0, bron.name)
    sleutels: set[str] = set()
    for bestand in bestanden:
        sleutels.update(_top_level_sleutels(bestand))
    return bestandsnamen, sorted(sleutels)


_DEFAULT = Registry()
_openai_parser = Parser(
    provider="openai",
    naam="openai",
    scoort=score_openai,
    parse=parse_openai_export,
)
_mistral_parser = Parser(
    provider="mistral",
    naam="mistral",
    scoort=score_mistral,
    parse=parse_mistral_export,
)
_DEFAULT.registreer(_openai_parser)
_DEFAULT.registreer(_mistral_parser)


def detecteer(bron: str | Path) -> str:
    """Detecteer de provider van een export zonder gebruikersinput."""
    return _DEFAULT.detecteer(bron)


def parseer(bron: str | Path) -> list[Gesprek]:
    """Parse een export naar het canonieke model."""
    return _DEFAULT.parseer(bron)


def analyseer_bron(bron: str | Path) -> tuple[str, str, list[Gesprek]]:
    """Detecteer en parse een export naar aanbieder, formaat en gesprekken."""
    return _DEFAULT.analyseer_bron(bron)


def registreer(parser: Parser) -> None:
    """Voeg een nieuwe parser toe aan de standaard registry (extensiepunt)."""
    _DEFAULT.registreer(parser)
