"""Bulk analyser (module 3 uit `specs/spec_bulk_analyser.md`).

Orkestreert de volledige pijplijn: een export innemen (zip of map), automatisch
detecteren en normaliseren via `structuur_detectie`, per assistant-bericht de
uitstoot berekenen via `carbon_calculator`, aggregeren per model, per maand,
per gesprek en per provider, en een JSON- en markdown-rapport produceren.
"""

from bulk_analyser.aggregatie import aggregeer, maand_van
from bulk_analyser.fouten import AnalyseFout
from bulk_analyser.modellen import (
    Aggregaat,
    AggregatieRapport,
    AnalyseRapport,
    Methode,
    OvergeslagenBericht,
)
from bulk_analyser.pijplijn import analyseer, vind_aanbieders
from bulk_analyser.rapport import genereeer_json, genereeer_markdown

__all__ = [
    "Aggregaat",
    "AggregatieRapport",
    "AnalyseFout",
    "AnalyseRapport",
    "Methode",
    "OvergeslagenBericht",
    "aggregeer",
    "analyseer",
    "genereeer_json",
    "genereeer_markdown",
    "maand_van",
    "vind_aanbieders",
]
