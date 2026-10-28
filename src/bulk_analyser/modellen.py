"""Datamodellen van de bulk analyser (aggregatie en rapport, FR-3).

Deze structuren zijn de machineleesbare tussenvormen tussen de aggregatie,
de pijplijn en de rapportage. Ze dragen geen provider-eigen velden, alleen
de canonieke aggregaten uit de spec.
"""

from dataclasses import dataclass

from carbon_calculator import WaardeBereik


@dataclass(frozen=True)
class Aggregaat:
    """De totalen van één deelgroep of van de hele export.

    Attributes:
        tokens: het aantal geschatte output-tokens.
        requests: het aantal modelaanvragen (assistant-berichten).
        energie: de energie in kWh als laag-hoog range over de zones.
        uitstoot: de uitstoot in kg CO2eq als laag-hoog range.
        aantal_onbekend_model: het aantal berichten met attributie 'onbekend'.
        aandeel_onbekend_model: aandeel daarvan op het aantal requests.
        provider: de provider van de groep, of None voor de maandgroepen.
        titel: de titel van het gesprek, alleen bij per-gesprek-groepen.
        gesprek_id: het id van het gesprek, alleen bij per-gesprek-groepen.
    """

    tokens: int
    requests: int
    energie: WaardeBereik
    uitstoot: WaardeBereik
    aantal_onbekend_model: int
    aandeel_onbekend_model: float
    provider: str | None = None
    titel: str | None = None
    gesprek_id: str | None = None


@dataclass(frozen=True)
class AggregatieRapport:
    """De aggregaten uit 'Aggregatie' van de spec.

    Attributes:
        totaal: het algemene totaal over de hele export.
        per_model: de totalen per modelattributie (ook 'onbekend').
        per_maand: de totalen per maand (UTC, op basis van created_at).
        per_gesprek: de totalen per gesprek, met titel en provider.
        per_provider: de totalen per provider voor gemengde exports.
    """

    totaal: Aggregaat
    per_model: dict[str, Aggregaat]
    per_maand: dict[str, Aggregaat]
    per_gesprek: dict[str, Aggregaat]
    per_provider: dict[str, Aggregaat]


@dataclass(frozen=True)
class OvergeslagenBericht:
    """Een assistant-bericht dat niet berekend kon worden (NFR-5).

    Attributes:
        bericht_id: het id van het bericht, of None.
        gesprek_id: het id van het gesprek waarin het bericht staat.
        reden: waarom het bericht is overgeslagen.
    """

    bericht_id: str | None
    gesprek_id: str
    reden: str


@dataclass(frozen=True)
class Methode:
    """De sectie 'methode en bronnen' uit de spec (FR-4).

    Attributes:
        aanbieders: de herkende aanbieder(s).
        formaat: het herkende formaat.
        tokenschatting: de gebruikte methode voor de tokenschatting.
        rekenkern: de rekenkern voor de impactberekening.
        versie_modelgegevens: de versie van de modelgegevens (A2).
        versie_module: de versie van dit pakket.
        zones: de aangenomen elektriciteitsmix-zones.
        bandbreedte: hoe de laag-hoog range tot stand komt.
        aantal_zonder_model: berichten zonder modelattributie.
        aantal_overgeslagen: berichten die niet berekend zijn.
        aantal_niet_westers: gemarkeerde berichten (FR-8).
        bronnen: bronverwijzingen bij de cijfers.
    """

    aanbieders: str
    formaat: str
    tokenschatting: str
    rekenkern: str
    versie_modelgegevens: str
    versie_module: str
    zones: str
    bandbreedte: str
    aantal_zonder_model: int
    aantal_overgeslagen: int
    aantal_niet_westers: int
    bronnen: tuple[str, ...]


@dataclass(frozen=True)
class AnalyseRapport:
    """Het volledige rapport van de bulk analyser (FR-3, FR-4).

    Attributes:
        herkende_aanbieder: de aanbieder of aanbieders van de export.
        herkende_formaat: het herkende exportformaat.
        aantal_gesprekken: het aantal gesprekken.
        aantal_berichten: het aantal verwerkte assistant-berichten.
        aggregaten: de aggregaties uit de spec.
        overgeslagen: de overgeslagen berichten met reden (NFR-5).
        waarschuwingen: globale waarschuwingen van de berekening.
        methode: de sectie 'methode en bronnen'.
    """

    herkende_aanbieder: str
    herkende_formaat: str
    aantal_gesprekken: int
    aantal_berichten: int
    aggregaten: AggregatieRapport
    overgeslagen: tuple[OvergeslagenBericht, ...]
    waarschuwingen: tuple[str, ...]
    methode: Methode
