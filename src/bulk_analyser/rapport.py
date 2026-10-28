"""Rapportage van de bulk analyser (stap 7 uit de spec).

`genereeer_json` levert een machineleesbaar, reproduceerbaar rapport met alle
aggregaten uit de spec. `genereeer_markdown` levert een mensleesbaar rapport
met de sectie 'methode en bronnen' (FR-3, FR-4, FR-1).
"""

import json
from typing import Any

from bulk_analyser.modellen import (
    Aggregaat,
    AggregatieRapport,
    AnalyseRapport,
    Methode,
)


def genereeer_json(rapport: AnalyseRapport) -> str:
    """Maak het machineleesbare JSON-rapport (FR-1, FR-3).

    Args:
        rapport: het analyse-rapport.

    Returns:
        De JSON-tekst. De ouput is deterministisch: dezelfde input geeft
        dezelfde output.
    """
    return json.dumps(_rapport_naar_dict(rapport), indent=2, ensure_ascii=False)


def _rapport_naar_dict(rapport: AnalyseRapport) -> dict[str, Any]:
    """Bouw de platte dict voor de JSON-output."""
    aandelen = rapport.aggregaten
    return {
        "herkende_aanbieder": rapport.herkende_aanbieder,
        "herkende_formaat": rapport.herkende_formaat,
        "aantal_gesprekken": rapport.aantal_gesprekken,
        "aantal_berichten": rapport.aantal_berichten,
        "totaal": _aggregaat_naar_dict(aandelen.totaal),
        "per_model": {
            naam: _aggregaat_naar_dict(ag, met_provider=True)
            for naam, ag in aandelen.per_model.items()
        },
        "per_maand": {
            maand: _aggregaat_naar_dict(ag) for maand, ag in aandelen.per_maand.items()
        },
        "per_gesprek": {
            id_: _aggregaat_naar_dict(ag, met_gesprek=True)
            for id_, ag in aandelen.per_gesprek.items()
        },
        "per_provider": {
            provider: _aggregaat_naar_dict(ag, met_provider=True)
            for provider, ag in aandelen.per_provider.items()
        },
        "overgeslagen": [
            {
                "bericht_id": item.bericht_id,
                "gesprek_id": item.gesprek_id,
                "reden": item.reden,
            }
            for item in rapport.overgeslagen
        ],
        "waarschuwingen": list(rapport.waarschuwingen),
        "methode_en_bronnen": _methode_naar_dict(rapport.methode),
    }


def _aggregaat_naar_dict(
    ag: Aggregaat, *, met_provider: bool = False, met_gesprek: bool = False
) -> dict[str, Any]:
    """Bouw de dict van één aggregaat, met de geldige velden per groep."""
    uit: dict[str, Any] = {
        "tokens": ag.tokens,
        "requests": ag.requests,
        "energie": _bereik_naar_dict(ag.energie),
        "uitstoot": _bereik_naar_dict(ag.uitstoot),
        "aantal_onbekend_model": ag.aantal_onbekend_model,
        "aandeel_onbekend_model": ag.aandeel_onbekend_model,
    }
    if met_gesprek:
        uit["gesprek_id"] = ag.gesprek_id
        uit["titel"] = ag.titel
        uit["provider"] = ag.provider
    elif met_provider:
        uit["provider"] = ag.provider
    return uit


def _bereik_naar_dict(bereik: Any) -> dict[str, float]:
    """Bouw de laag-hoog range van een WaardeBereik voor de JSON-output."""
    return {
        "laag": bereik.laag,
        "hoog": bereik.hoog,
        "gemiddelde": bereik.gemiddelde,
    }


def _methode_naar_dict(methode: Methode) -> dict[str, Any]:
    """Bouw de sectie 'methode en bronnen' voor de JSON-output."""
    return {
        "aanbieder": methode.aanbieders,
        "formaat": methode.formaat,
        "tokenschatting": methode.tokenschatting,
        "rekenkern": methode.rekenkern,
        "versie_modelgegevens": methode.versie_modelgegevens,
        "versie_module": methode.versie_module,
        "zones": methode.zones,
        "bandbreedte": methode.bandbreedte,
        "aantal_zonder_model": methode.aantal_zonder_model,
        "aantal_overgeslagen": methode.aantal_overgeslagen,
        "aantal_niet_westers": methode.aantal_niet_westers,
        "bronnen": list(methode.bronnen),
    }


def genereeer_markdown(rapport: AnalyseRapport) -> str:
    """Maak het mensleesbare markdown-rapport (FR-4).

    Args:
        rapport: het analyse-rapport.

    Returns:
        De markdown-tekst met een sectie 'methode en bronnen' en een
        bronverwijzing bij elk cijfer.
    """
    lijnen: list[str] = [
        "# Koolstofrapport van de chat-export",
        "",
        f"- herkende aanbieder: {rapport.herkende_aanbieder}",
        f"- herkende formaat: {rapport.herkende_formaat}",
        f"- gesprekken: {rapport.aantal_gesprekken}",
        f"- berichten (assistant): {rapport.aantal_berichten}",
        "",
        "## Totaal",
        *_totaal_regels(rapport.aggregaten),
        "",
        "## Per model",
        *_model_regels(rapport.aggregaten),
        "",
        "## Per maand (UTC)",
        *_maand_regels(rapport.aggregaten),
        "",
        "## Per gesprek",
        *_gesprek_regels(rapport.aggregaten),
        "",
        "## Per provider",
        *_provider_regels(rapport.aggregaten),
        "",
        "## Overgeslagen berichten",
        *_overgeslagen_regels(rapport),
        "",
        "## Methode en bronnen",
        *_methode_regels(rapport.methode),
        "",
        "## Waarschuwingen",
        *_waarschuwingen_regels(rapport),
        "",
    ]
    return "\n".join(lijnen)


def _totaal_regels(aggregaten: AggregatieRapport) -> list[str]:
    """Geef de regels van het algemene totaal."""
    totaal = aggregaten.totaal
    return [
        f"- tokens: {totaal.tokens}",
        f"- requests: {totaal.requests}",
        f"- energie: {totaal.energie.laag:.4f} tot {totaal.energie.hoog:.4f} "
        f"kWh (gemiddelde {totaal.energie.gemiddelde:.4f})",
        f"- uitstoot: {totaal.uitstoot.laag:.6f} tot {totaal.uitstoot.hoog:.6f} "
        f"kg CO2eq (gemiddelde {totaal.uitstoot.gemiddelde:.6f})",
        f"- onbekende modellen: {totaal.aantal_onbekend_model} "
        f"({totaal.aandeel_onbekend_model:.1%})",
    ]


def _model_regels(aggregaten: AggregatieRapport) -> list[str]:
    """Geef de regels van de tabel per model."""
    regels = [
        "| model | provider | tokens | requests | kWh | kg CO2eq |",
        "|---|---|---|---|---|---|",
    ]
    for naam, ag in sorted(aggregaten.per_model.items()):
        regels.append(
            f"| {naam} | {ag.provider or ''} | {ag.tokens} | {ag.requests} | "
            f"{ag.energie.gemiddelde:.4f} | {ag.uitstoot.gemiddelde:.6f} |"
        )
    if not aggregaten.per_model:
        regels.append("_geen_")
    return regels


def _maand_regels(aggregaten: AggregatieRapport) -> list[str]:
    """Geef de regels van de tabel per maand."""
    regels = ["| maand | tokens | requests | kWh | kg CO2eq |", "|---|---|---|---|---|"]
    for maand, ag in sorted(aggregaten.per_maand.items()):
        regels.append(
            f"| {maand} | {ag.tokens} | {ag.requests} | "
            f"{ag.energie.gemiddelde:.4f} | {ag.uitstoot.gemiddelde:.6f} |"
        )
    if not aggregaten.per_maand:
        regels.append("_geen_")
    return regels


def _gesprek_regels(aggregaten: AggregatieRapport) -> list[str]:
    """Geef de regels van de tabel per gesprek."""
    regels = [
        "| gesprek | titel | provider | requests | kWh | kg CO2eq |",
        "|---|---|---|---|---|---|",
    ]
    for id_, ag in sorted(aggregaten.per_gesprek.items()):
        regels.append(
            f"| {id_} | {ag.titel or ''} | {ag.provider or ''} | {ag.requests} | "
            f"{ag.energie.gemiddelde:.4f} | {ag.uitstoot.gemiddelde:.6f} |"
        )
    if not aggregaten.per_gesprek:
        regels.append("_geen_")
    return regels


def _provider_regels(aggregaten: AggregatieRapport) -> list[str]:
    """Geef de regels van de tabel per provider."""
    regels = ["| provider | tokens | requests | kWh | kg CO2eq |", "|---|---|---|---|---|"]
    for provider, ag in sorted(aggregaten.per_provider.items()):
        regels.append(
            f"| {provider} | {ag.tokens} | {ag.requests} | "
            f"{ag.energie.gemiddelde:.4f} | {ag.uitstoot.gemiddelde:.6f} |"
        )
    if not aggregaten.per_provider:
        regels.append("_geen_")
    return regels


def _overgeslagen_regels(rapport: AnalyseRapport) -> list[str]:
    """Geef de regels met elk overgeslagen bericht en de reden (NFR-5)."""
    if not rapport.overgeslagen:
        return ["_geen_"]
    return [
        f"- {item.bericht_id or 'zonder id'} (gesprek {item.gesprek_id}): "
        f"{item.reden}"
        for item in rapport.overgeslagen
    ]


def _methode_regels(methode: Methode) -> list[str]:
    """Geef de sectie 'methode en bronnen' met een bron per cijfer (FR-4)."""
    regels = [
        f"- herkende aanbieder: {methode.aanbieders}",
        f"- herkende formaat: {methode.formaat}",
        f"- tokenschatting: {methode.tokenschatting}",
        f"- rekenkern: {methode.rekenkern}, versie van de modelgegevens: "
        f"{methode.versie_modelgegevens} (versie module {methode.versie_module})",
        f"- aangenomen elektriciteitsmix-zones: {methode.zones}",
        f"- laag-hoog bandbreedte: {methode.bandbreedte}",
        f"- aantal berichten zonder model: {methode.aantal_zonder_model}",
        f"- aantal overgeslagen: {methode.aantal_overgeslagen}",
        f"- aantal niet-westerse berichten: {methode.aantal_niet_westers}",
        "- bronnen:",
    ]
    regels.extend(f"  - {bron}" for bron in methode.bronnen)
    return regels


def _waarschuwingen_regels(rapport: AnalyseRapport) -> list[str]:
    """Geef de waarschuwingen van de berekening."""
    if not rapport.waarschuwingen:
        return ["_geen_"]
    return [f"- {waarschuwing}" for waarschuwing in rapport.waarschuwingen]
