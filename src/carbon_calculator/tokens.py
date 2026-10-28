"""Tokenschatting en niet-westerse tekstherkenning (FR-1, FR-8).

De vuistregel uit de spec is 1 token per 4 tekens en gebruikt alleen de
standaardbibliotheek. tiktoken wordt alleen in tests gebruikt.
"""

import unicodedata

_CHARS_PER_TOKEN = 4
_NIET_WESTERS_MIN_TEKENS = 5
_NIET_WESTERS_MIN_AANDEEL = 0.10


def schat_tokens(inhoud: str) -> int:
    """Schat het aantal tokens van een tekst met de vuistregel uit de spec.

    De schatting is deterministisch: dezelfde invoer geeft altijd dezelfde
    uitkomst (FR-1).

    Args:
        inhoud: de tekst van het bericht.

    Returns:
        Het geschatte aantal tokens (lengte gedeeld door 4, naar beneden).
    """
    return len(inhoud) // _CHARS_PER_TOKEN


def _is_niet_westers_teken(teken: str) -> bool:
    """Of een enkel teken buiten de westerse Latijnse blokken valt.

    Whitespace, cijfers, interpunctie en wiskundige symbolen tellen niet als
    niet-westers, ook al liggen ze buiten het Latijnse alfabet.
    """
    if teken.isspace() or teken.isdigit():
        return False
    categorie = unicodedata.category(teken)
    if categorie.startswith("P") or categorie == "Sm":
        return False
    naam = unicodedata.name(teken, "")
    return not naam.startswith("LATIN")


def aandeel_niet_westerse_tekens(inhoud: str) -> float:
    """Het aandeel niet-westerse tekens in een tekst, tussen 0.0 en 1.0.

    Args:
        inhoud: de tekst van het bericht.

    Returns:
        Het aandeel tekens buiten de westerse Latijnse blokken.
    """
    if not inhoud:
        return 0.0
    telling = sum(1 for teken in inhoud if _is_niet_westers_teken(teken))
    return telling / len(inhoud)


def is_niet_westers(inhoud: str) -> bool:
    """Of een bericht gemarkeerd moet worden als niet-westerse tekst (FR-8).

    De vuistregel van 1 token per 4 tekens onderschat teksten met veel
    niet-westerse tekens sterk, daarom markeert de module die berichten.

    Een bericht wordt gemarkeerd wanneer het minstens `_NIET_WESTERS_MIN_TEKENS`
    niet-westerse tekens bevat én het aandeel daarvan minstens
    `_NIET_WESTERS_MIN_AANDEEL` is.

    Args:
        inhoud: de tekst van het bericht.

    Returns:
        True als het bericht voldoet aan de markeerregel.
    """
    if len(inhoud) < _NIET_WESTERS_MIN_TEKENS:
        return False
    return aandeel_niet_westerse_tekens(inhoud) >= _NIET_WESTERS_MIN_AANDEEL
