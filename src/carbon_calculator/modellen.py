"""Modelattributie volgens de volgorde uit de spec (FR-2).

Volgorde voor openai: het `model_slug` uit de metadata van het
assistant-bericht, anders het `default_model_slug` van het gesprek, anders
`onbekend`. De exports van mistral bevatten geen modelinformatie, daarom is de
attributie daar altijd `onbekend`.
"""

from carbon_calculator.config import BerekenConfig
from structuur_detectie import Bericht, Gesprek

ONBEKEND_MODEL = "onbekend"


def bepaal_model(bericht: Bericht, gesprek: Gesprek, config: BerekenConfig) -> str:
    """Bepaal de modelattributie van een assistant-bericht.

    Args:
        bericht: het canonieke bericht, met een eventueel `model_slug`.
        gesprek: het canonieke gesprek, als bron van `default_model_slug`.
        config: bevat de gesprek-standaardmodellen uit de export (optioneel).

    Returns:
        De modelwaarde, of `ONBEKEND_MODEL` als geen van de bronnen een model
        oplevert.
    """
    if bericht.model is not None:
        return bericht.model
    gesprek_model = config.gesprek_standaard_modellen.get(gesprek.id)
    if gesprek_model is not None:
        return gesprek_model
    return ONBEKEND_MODEL
