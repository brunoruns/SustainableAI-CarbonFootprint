"""Fouttypes voor structuurdetectie en -parsing."""


class ParseFout(Exception):
    """De input voldeed niet aan het verwachte exportformaat."""


class OnbekendFormaatError(Exception):
    """Geen enkele geregistreerde parser herkende de export.

    Attributes:
        bestandsnamen: de gevonden bestandsnamen in de export.
        json_sleutels: de gevonden top-level JSON-sleutels.
    """

    def __init__(
        self,
        melding: str,
        *,
        bestandsnamen: list[str],
        json_sleutels: list[str],
    ) -> None:
        super().__init__(melding)
        self.bestandsnamen = bestandsnamen
        self.json_sleutels = json_sleutels
