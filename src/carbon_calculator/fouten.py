"""Fouttypes voor de carbon calculator."""


class OngeldigeZoneError(Exception):
    """De elektriciteitsmix-zone wordt niet door EcoLogits ondersteund (FR-5)."""


class OngeldigeProviderError(Exception):
    """De provider wordt in v1 van de calculator niet ondersteund."""


class ModelOnbekendBijEcoLogits(Exception):
    """Het model is niet geregistreerd in de modelgegevens van EcoLogits."""


class EcoLogitsFout(Exception):
    """EcoLogits gaf een onverwachte fout terug."""
