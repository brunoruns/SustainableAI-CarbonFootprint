"""Het canonieke model van een chat export.

Dit model is de enige interface tussen modules (zie spec_structuur_detectie.md).
"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Bericht:
    """Een enkel bericht in een gesprek."""

    id: str | None
    rol: str
    inhoud: str
    created_at: float | str | None
    model: str | None

    def naar_dict(self) -> dict[str, Any]:
        """Geef het bericht als platte dict, zonder provider-eigen velden."""
        return asdict(self)


@dataclass(frozen=True)
class Gesprek:
    """Een gesprek met chronologisch gesorteerde berichten."""

    id: str
    titel: str | None
    provider: str
    created_at: float | str | None
    berichten: list[Bericht]

    def naar_dict(self) -> dict[str, Any]:
        """Geef het gesprek als platte dict, zonder provider-eigen velden."""
        return asdict(self)
