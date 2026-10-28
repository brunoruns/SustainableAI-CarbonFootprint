"""Fouttypes van de bulk analyser (FR-5).

Elke fout wijst de gebruiker naar de stap en de oorzaak, zonder crash en
zonder stil verkeerde output.
"""


class AnalyseFout(Exception):
    """Een stap in de bulk-pijplijn is mislukt.

    Attributes:
        stap: de fase waar de fout optrad (bijvoorbeeld 'invoer' of 'detectie').
        oorzaak: een beschrijving van de oorzaak, gericht aan de gebruiker.
    """

    def __init__(self, *, stap: str, oorzaak: str) -> None:
        super().__init__(f"[stap '{stap}'] {oorzaak}")
        self.stap = stap
        self.oorzaak = oorzaak
