"""De CLI `co2chat`: een dunne wrapper om de bulk-pijplijn.

De CLI bevat geen eigen reken- of aggregatielogica (NFR-5 uit
`specs/spec_cli.md`): hij verzorgt alleen de invoer (argparse), de mapping
van vlaggen naar `BerekenConfig` (FR-4), de uitvoer (JSON of markdown via
`genereeer_json` en `genereeer_markdown`) en de foutafhandeling met de
juiste exitcodes (FR-5, FR-6). Er komt geen netwerkverkeer op gang (NFR-2).
"""

import argparse
import importlib.metadata
import sys
from pathlib import Path

from bulk_analyser import (
    AnalyseFout,
    analyseer,
    genereeer_json,
    genereeer_markdown,
    vind_aanbieders,
)
from carbon_calculator import BerekenConfig, OngeldigeZoneError
from structuur_detectie import OnbekendFormaatError, ParseFout

_PAKKET_NAAM = "sustainable-ai-carbonfootprint"


def _versie() -> str:
    """Geef de projectversie uit de package-metadata, of 'onbekend'."""
    try:
        return importlib.metadata.version(_PAKKET_NAAM)
    except importlib.metadata.PackageNotFoundError:
        return "onbekend"


def _bouw_parser() -> argparse.ArgumentParser:
    """Bouw de argparse-interface van `co2chat`."""
    parser = argparse.ArgumentParser(
        prog="co2chat",
        description=(
            "Analyseer de carbon footprint van een chat export (map, bestand "
            "of .zip) en print een markdown- of JSON-rapport."
        ),
    )
    parser.add_argument(
        "bron", help="pad naar een map, bestand of .zip van een chat export"
    )
    formaat = parser.add_mutually_exclusive_group()
    formaat.add_argument(
        "-j", "--json", action="store_true", help="schrijf het rapport als JSON"
    )
    formaat.add_argument(
        "--markdown", action="store_true", help="schrijf als markdown (expliciet)"
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="PAD",
        help="schrijf naar een bestand in plaats van stdout",
    )
    parser.add_argument(
        "--zone",
        metavar="ZONE",
        help="elektriciteitsmix-zone voor alle providers (bijvoorbeeld WOR, EEE, USA)",
    )
    parser.add_argument(
        "--model",
        metavar="MODEL",
        help="standaardmodel voor providers zonder modelinformatie",
    )
    parser.add_argument(
        "--fallback-model",
        metavar="MODEL",
        help="fallback-model voor berichten met attributie 'onbekend'",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"co2chat {_versie()}",
        help="print de versie en stop",
    )
    return parser


def _bouw_config(args: argparse.Namespace, bron: str) -> BerekenConfig:
    """Map de CLI-vlaggen op de `BerekenConfig` (FR-4).

    `--zone` en `--model` worden per gedetecteerde aanbieder ingevuld,
    `--fallback-model` is globaal. Zonder vlaggen is de config de default van
    de calculator, precies zoals de pijplijn die los aanroept.

    Args:
        args: de geparsede commandoregelargumenten.
        bron: de export (map, bestand of zip) waarvan de aanbieders
            gedetecteerd worden.

    Returns:
        De config voor de pijplijn.
    """
    if args.zone is None and args.model is None and args.fallback_model is None:
        return BerekenConfig()
    aanbieders: tuple[str, ...] = ()
    if args.zone is not None or args.model is not None:
        aanbieders = vind_aanbieders(bron)
    return BerekenConfig(
        zones_per_provider=(
            {aanbieder: args.zone for aanbieder in aanbieders}
            if args.zone is not None
            else {}
        ),
        provider_standaard_modellen=(
            {aanbieder: args.model for aanbieder in aanbieders}
            if args.model is not None
            else {}
        ),
        fallback_model=args.fallback_model,
    )


def _bepaal_formaat(args: argparse.Namespace) -> str:
    """Kies 'json' of 'markdown' uit de vlaggen en de output-extensie."""
    if args.json:
        return "json"
    if args.markdown:
        return "markdown"
    if args.output is not None and Path(args.output).suffix.lower() == ".json":
        return "json"
    return "markdown"


def _schrijf(tekst: str, output: str | None) -> None:
    """Schrijf de rapport-tekst naar een bestand of naar stdout."""
    if output is None:
        sys.stdout.write(tekst)
        return
    Path(output).write_text(tekst, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Voer de CLI uit en geef de exitcode terug.

    Args:
        argv: de commandoregelargumenten, of None voor `sys.argv[1:]`.

    Returns:
        0 bij succes, 1 bij een fout uit de modules of bij het schrijven
        (FR-5). Gebruikersfouten in de commandoregel stoppen via argparse
        met exitcode 2 (FR-6).
    """
    parser = _bouw_parser()
    args = parser.parse_args(argv)
    try:
        config = _bouw_config(args, args.bron)
        rapport = analyseer(args.bron, config)
        tekst = (
            genereeer_json(rapport)
            if _bepaal_formaat(args) == "json"
            else genereeer_markdown(rapport)
        )
        _schrijf(tekst, args.output)
    except (
        AnalyseFout,
        OnbekendFormaatError,
        ParseFout,
        OngeldigeZoneError,
        OSError,
    ) as fout:
        print(f"fout: {fout}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
