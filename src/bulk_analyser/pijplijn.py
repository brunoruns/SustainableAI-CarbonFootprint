"""De bulk-pijplijn: invoer, uitpakken, detectie, berekening (stap 1 t/m 5).

Neemt een zip of een map met een export, herkent per bron de aanbieder en het
formaat (module 1), berekent de impact (module 2) en stelt de aggregaten en het
rapport samen. Elke stap kan falen met een duidelijke `AnalyseFout` (FR-5).
"""

import tempfile
import zipfile
from pathlib import Path

import structuur_detectie
from bulk_analyser.aggregatie import aggregeer
from bulk_analyser.fouten import AnalyseFout
from bulk_analyser.modellen import AnalyseRapport, Methode, OvergeslagenBericht
from carbon_calculator import (
    BerekenConfig,
    BerekeningRapport,
    GesprekBerekening,
    bereken_gesprekken,
)
from structuur_detectie import Gesprek


def analyseer(
    bron: str | Path, config: BerekenConfig | None = None
) -> AnalyseRapport:
    """Analyseer een export end-to-end tot een volledig rapport (FR-1).

    Args:
        bron: een map, een bestand of een zip met de export.
        config: de berekeningsconfiguratie; de default gebruikt WOR.

    Returns:
        Het analyse-rapport met aggregaten, overgeslagen berichten en de
        sectie 'methode en bronnen'.

    Raises:
        AnalyseFout: bij een ontbrekende of ongeldige input; de fout noemt
            de stap en de oorzaak (FR-5).
    """
    config = config if config is not None else BerekenConfig()
    pad = Path(bron)
    if not pad.exists():
        raise AnalyseFout(
            stap="invoer", oorzaak=f"export niet gevonden op '{pad}'"
        )
    if pad.suffix.lower() == ".zip":
        return _analyseer_zip(pad, config)
    return _analyseer_bron(pad, config)


def vind_aanbieders(bron: str | Path) -> tuple[str, ...]:
    """Detecteer de aanbieders in een export (map, bestand of zip).

    De CLI gebruikt deze helper om `--zone` en `--model` per gedetecteerde
    aanbieder in de config te zetten (FR-4 uit `specs/spec_cli.md`), zodat de
    CLI geen eigen detectielogica nodig heeft (A3). De detectie is dezelfde
    als die van `analyseer`, alleen zonder berekening en aggregatie.

    Args:
        bron: een map, een bestand of een zip met de export.

    Returns:
        De unieke aanbieders in volgorde van detectie.

    Raises:
        AnalyseFout: bij een ontbrekende of ongeldige input; de fout noemt
            de stap en de oorzaak (FR-5).
    """
    pad = Path(bron)
    if not pad.exists():
        raise AnalyseFout(
            stap="invoer", oorzaak=f"export niet gevonden op '{pad}'"
        )
    if pad.suffix.lower() == ".zip":
        return _vind_aanbieders_in_zip(pad)
    return _vind_aanbieders_in_bron(pad)


def _vind_aanbieders_in_zip(pad: Path) -> tuple[str, ...]:
    """Detecteer de aanbieders in een uitgepakte zip."""
    try:
        with zipfile.ZipFile(pad) as archief, tempfile.TemporaryDirectory(
            prefix="bulk-analyser-"
        ) as tmp:
            archief.extractall(tmp)
            return _vind_aanbieders_in_bron(Path(tmp))
    except zipfile.BadZipFile as fout:
        raise AnalyseFout(
            stap="invoer", oorzaak=f"'{pad.name}' is geen geldige zip: {fout}"
        ) from fout
    except OSError as fout:
        raise AnalyseFout(
            stap="invoer", oorzaak=f"kon de zip '{pad.name}' niet uitpakken: {fout}"
        ) from fout


def _vind_aanbieders_in_bron(bron: Path) -> tuple[str, ...]:
    """Geef de unieke aanbieders van de herkenbare exports onder een bron."""
    aanbieders: list[str] = []
    for export_bron in _vind_export_bronnen(bron):
        provider, _, _ = _detecteer_en_parse(export_bron)
        if provider not in aanbieders:
            aanbieders.append(provider)
    return tuple(aanbieders)


def _analyseer_zip(pad: Path, config: BerekenConfig) -> AnalyseRapport:
    """Pak een zip uit in een tijdelijke map en analyseer de inhoud (FR-1)."""
    try:
        with zipfile.ZipFile(pad) as archief, tempfile.TemporaryDirectory(
            prefix="bulk-analyser-"
        ) as tmp:
            archief.extractall(tmp)
            return _analyseer_bron(Path(tmp), config)
    except zipfile.BadZipFile as fout:
        raise AnalyseFout(
            stap="invoer", oorzaak=f"'{pad.name}' is geen geldige zip: {fout}"
        ) from fout
    except OSError as fout:
        raise AnalyseFout(
            stap="invoer", oorzaak=f"kon de zip '{pad.name}' niet uitpakken: {fout}"
        ) from fout


def _analyseer_bron(bron: Path, config: BerekenConfig) -> AnalyseRapport:
    """Detecteer, parse en bereken alle exports onder een bron (FR-5, FR-6)."""
    bronnen = _vind_export_bronnen(bron)
    if not bronnen:
        raise AnalyseFout(
            stap="detectie",
            oorzaak=(
                f"geen herkenbare export gevonden in '{bron}'; de export moet "
                "een conversations.json of een chat-export-... map met "
                "chat-*.json bestanden bevatten"
            ),
        )
    gesprekken: list[Gesprek] = []
    aanbieders: list[str] = []
    formaten: list[str] = []
    for export_bron in bronnen:
        provider, formaat, export_gesprekken = _detecteer_en_parse(export_bron)
        if provider not in aanbieders:
            aanbieders.append(provider)
        if formaat not in formaten:
            formaten.append(formaat)
        gesprekken.extend(export_gesprekken)
    if not gesprekken:
        raise AnalyseFout(
            stap="detectie", oorzaak="de export bevatte geen gesprekken"
        )

    berekening = bereken_gesprekken(gesprekken, config)
    aggregaten = aggregeer(gesprekken, berekening)
    overgeslagen = _verzamel_overgeslagen(gesprekken, berekening)
    methode = _stel_methode_op(aanbieders, formaten, berekening)
    return AnalyseRapport(
        herkende_aanbieder=", ".join(aanbieders),
        herkende_formaat=", ".join(formaten),
        aantal_gesprekken=len(gesprekken),
        aantal_berichten=berekening.aantal_berichten,
        aggregaten=aggregaten,
        overgeslagen=overgeslagen,
        waarschuwingen=berekening.waarschuwingen,
        methode=methode,
    )


def _detecteer_en_parse(bron: Path) -> tuple[str, str, list[Gesprek]]:
    """Detecteer en parse één exportbron, met een duidelijke fout (FR-5)."""
    try:
        return structuur_detectie.analyseer_bron(bron)
    except structuur_detectie.OnbekendFormaatError as fout:
        raise AnalyseFout(stap="detectie", oorzaak=str(fout)) from fout
    except structuur_detectie.ParseFout as fout:
        raise AnalyseFout(stap="detectie", oorzaak=str(fout)) from fout


def _vind_export_bronnen(root: Path) -> list[Path]:
    """Vind de detecteerbare exportbronnen onder een map of bestand.

    Elke bron is ofwel een `conversations.json`-bestand ofwel een
    `chat-export-...`-map. Geneste bronnen binnen een chat-export-map worden
    niet dubbel meegenomen.
    """
    if root.is_file():
        return [root]
    bronnen: list[Path] = []
    if root.name.startswith("chat-export-"):
        bronnen.append(root)
    for pad in root.glob("**/conversations.json"):
        if not _ligt_in_chat_export_map(pad):
            bronnen.append(pad)
    for pad in root.glob("**/"):
        if pad.name.startswith("chat-export-") and pad != root:
            bronnen.append(pad)
    uniek: list[Path] = []
    gezien: set[Path] = set()
    for bron in bronnen:
        if bron not in gezien:
            gezien.add(bron)
            uniek.append(bron)
    return uniek


def _ligt_in_chat_export_map(pad: Path) -> bool:
    """Of een pad binnen een `chat-export-...`-map ligt."""
    return any(deel.name.startswith("chat-export-") for deel in pad.parents)


def _verzamel_overgeslagen(
    gesprekken: list[Gesprek], berekening: BerekeningRapport
) -> tuple[OvergeslagenBericht, ...]:
    """Verzamel alle overgeslagen berichten met reden (NFR-5)."""
    per_id: dict[str, GesprekBerekening] = {
        berekening_gesprek.gesprek_id: berekening_gesprek
        for berekening_gesprek in berekening.gesprekken
    }
    uit: list[OvergeslagenBericht] = []
    for gesprek in gesprekken:
        berekening_gesprek = per_id.get(gesprek.id)
        if berekening_gesprek is None:
            continue
        for bericht in berekening_gesprek.berichten:
            if bericht.overgeslagen:
                uit.append(
                    OvergeslagenBericht(
                        bericht_id=bericht.bericht_id,
                        gesprek_id=gesprek.id,
                        reden=bericht.reden if bericht.reden else "onbekende reden",
                    )
                )
    return tuple(uit)


def _stel_methode_op(
    aanbieders: list[str],
    formaten: list[str],
    berekening: BerekeningRapport,
) -> Methode:
    """Bouw de sectie 'methode en bronnen' uit het rapport (FR-4)."""
    return Methode(
        aanbieders=", ".join(aanbieders),
        formaat=", ".join(formaten),
        tokenschatting="vuistregel uit de spec: 1 token per 4 tekens",
        rekenkern="EcoLogits",
        versie_modelgegevens=berekening.versie_modelgegevens,
        versie_module=berekening.versie_module,
        zones="WOR als default, datacenterregio per provider, EEE als reserve",
        bandbreedte=(
            "elke berekening draait voor minstens twee zones; de laag-hoog "
            "range is het minimum en maximum van de zone-gemiddelden"
        ),
        aantal_zonder_model=berekening.aantal_onbekend_model,
        aantal_overgeslagen=berekening.aantal_overgeslagen,
        aantal_niet_westers=berekening.aantal_niet_westers,
        bronnen=(
            "energie- en emissiefactoren: EcoLogits modelgegevens",
            "datacenterregio's: src/carbon_calculator/data/datacenter_regios.json",
            "architectuurkeuze: docs/ADR/carbon-calculator.md",
        ),
    )
