"""Module 1: structuurdetectie en parsing van chat exports."""

from structuur_detectie.canoniek import Bericht, Gesprek
from structuur_detectie.detectie import (
    Parser,
    Registry,
    analyseer_bron,
    detecteer,
    parseer,
    registreer,
)
from structuur_detectie.fouten import OnbekendFormaatError, ParseFout

__all__ = [
    "Bericht",
    "Gesprek",
    "OnbekendFormaatError",
    "ParseFout",
    "Parser",
    "Registry",
    "analyseer_bron",
    "detecteer",
    "parseer",
    "registreer",
]
