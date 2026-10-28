"""Numerieke hulpstructuur voor de calculator."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WaardeBereik:
    """Een laag-hoog bereik met een gemiddelde (FR-4)."""

    laag: float
    hoog: float
    gemiddelde: float

    def __add__(self, ander: "WaardeBereik") -> "WaardeBereik":
        return WaardeBereik(
            laag=self.laag + ander.laag,
            hoog=self.hoog + ander.hoog,
            gemiddelde=self.gemiddelde + ander.gemiddelde,
        )
