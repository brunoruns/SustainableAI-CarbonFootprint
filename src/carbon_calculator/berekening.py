"""De rekenstap per assistant-bericht en het rapport van de calculator.

Hier ligt de orkestratie uit 'Rekenstap per bericht' van de spec: tokens
schatten, model attribueren, EcoLogits aanroepen voor minstens twee zones en
het resultaat per bericht bewaren (FR-4 t/m FR-7, NFR-2). De eigenlijke
energie- en emissiewaarden komen alleen uit EcoLogits (FR-3).
"""

import importlib.metadata
import math
from dataclasses import dataclass

import ecologits

from carbon_calculator.config import STANDAARD_PROVIDER_MODELLEN, BerekenConfig
from carbon_calculator.ecologits_koppeling import schat_impact
from carbon_calculator.fouten import ModelOnbekendBijEcoLogits
from carbon_calculator.modellen import ONBEKEND_MODEL, bepaal_model
from carbon_calculator.numeriek import WaardeBereik
from carbon_calculator.tokens import is_niet_westers, schat_tokens
from carbon_calculator.zones import bepaal_zones
from structuur_detectie import Bericht, Gesprek

_PACKAGE_NAAM = "sustainable-ai-carbonfootprint"
_NUL = WaardeBereik(0.0, 0.0, 0.0)


def _moduleversie() -> str:
    """De versie van dit pakket, of 'onbekend' als die niet te vinden is."""
    try:
        return importlib.metadata.version(_PACKAGE_NAAM)
    except importlib.metadata.PackageNotFoundError:
        return "onbekend"


@dataclass(frozen=True)
class ZoneUitkomst:
    """De uitkomst van een berekening voor één elektriciteitsmix-zone."""

    zone: str
    energie: WaardeBereik
    uitstoot: WaardeBereik


@dataclass(frozen=True)
class BerichtBerekening:
    """De berekening van één assistant-bericht (FR-4, FR-7, FR-8).

    Attributes:
        bericht_id: het id van het canonieke bericht.
        attributie: de modelwaarde volgens de attributieregels, of 'onbekend'.
        model: het model waarmee daadwerkelijk gerekend is, of None bij een
            overgeslagen bericht.
        tokens: de geschatte hoeveelheid output-tokens.
        niet_westers: of de tekst gemarkeerd is via FR-8.
        latency: de gebruikte request-latency in seconden.
        latency_aangenomen: True als geen latency gemeten was (A4).
        zones: de gebruikte elektriciteitsmix-zones (minstens twee, FR-6).
        uitkomsten_per_zone: de EcoLogits-uitkomst per zone.
        energie: de laag-hoog range van de energie in kWh over de zones.
        uitstoot: de laag-hoog range van de uitstoot in kg CO2eq over de zones.
        versie_modelgegevens: de versie van de EcoLogits-modelgegevens (A2).
        waarschuwingen: waarschuwingen van de berekening (FR-7).
        overgeslagen: of het bericht niet meegeteld is (FR-7).
        reden: waarom het bericht is overgeslagen, of None.
    """

    bericht_id: str | None
    attributie: str
    model: str | None
    tokens: int
    niet_westers: bool
    latency: float
    latency_aangenomen: bool
    zones: tuple[str, ...]
    uitkomsten_per_zone: tuple[ZoneUitkomst, ...]
    energie: WaardeBereik | None
    uitstoot: WaardeBereik | None
    versie_modelgegevens: str
    waarschuwingen: tuple[str, ...]
    overgeslagen: bool
    reden: str | None


@dataclass(frozen=True)
class GesprekBerekening:
    """De som van de berekeningen binnen één gesprek."""

    gesprek_id: str
    provider: str
    berichten: tuple[BerichtBerekening, ...]
    totale_energie: WaardeBereik
    totale_uitstoot: WaardeBereik
    totaal_tokens: int
    aantal_overgeslagen: int
    aantal_onbekend_model: int
    aantal_niet_westers: int


@dataclass(frozen=True)
class BerekeningRapport:
    """Het totale resultaat van de calculator voor een export.

    Attributes:
        versie_modelgegevens: de versie van de EcoLogits-modelgegevens (A2).
        versie_module: de versie van dit pakket.
        aantal_berichten: het aantal verwerkte assistant-berichten.
        aantal_overgeslagen: het aantal berichten dat niet meegeteld is (FR-7).
        aantal_onbekend_model: het aantal berichten met attributie 'onbekend'.
        aantal_niet_westers: het aantal gemarkeerde berichten (FR-8).
        totaal_tokens: het totale aantal geschatte tokens.
        totale_energie: de totale energie in kWh als range over de zones.
        totale_uitstoot: de totale uitstoot in kg CO2eq als range.
        gesprekken: de berekening per gesprek.
        waarschuwingen: globale waarschuwingen, bijvoorbeeld over de latency.
    """

    versie_modelgegevens: str
    versie_module: str
    aantal_berichten: int
    aantal_overgeslagen: int
    aantal_onbekend_model: int
    aantal_niet_westers: int
    totaal_tokens: int
    totale_energie: WaardeBereik
    totale_uitstoot: WaardeBereik
    gesprekken: tuple[GesprekBerekening, ...]
    waarschuwingen: tuple[str, ...]


def _tel_op(waarden: list[WaardeBereik]) -> WaardeBereik:
    """Tel bereiken op; een lege lijst geeft een nulbereik."""
    if not waarden:
        return _NUL
    totaal = waarden[0]
    for waarde in waarden[1:]:
        totaal = totaal + waarde
    return totaal


def _bandbreedte(uitkomsten: tuple[WaardeBereik, ...]) -> WaardeBereik:
    """Bereken de laag-hoog range over de zones (FR-6).

    De uitkomst van een zone is het gemiddelde dat EcoLogits voor die zone
    berekent; laag en hoog zijn het minimum en maximum over die
    zone-gemiddelden, zodat de invloed van de zonekeuze zichtbaar blijft.
    """
    gemiddelden = [uitkomst.gemiddelde for uitkomst in uitkomsten]
    return WaardeBereik(
        laag=min(gemiddelden),
        hoog=max(gemiddelden),
        gemiddelde=sum(gemiddelden) / len(gemiddelden),
    )


def _overgeslagen_bericht(
    bericht: Bericht,
    attributie: str,
    tokens: int,
    niet_westers: bool,
    versie: str,
    reden: str,
    waarschuwingen: list[str],
) -> BerichtBerekening:
    """Markeer een bericht als overgeslagen met een duidelijke reden (FR-7)."""
    return BerichtBerekening(
        bericht_id=bericht.id,
        attributie=attributie,
        model=None,
        tokens=tokens,
        niet_westers=niet_westers,
        latency=0.0,
        latency_aangenomen=True,
        zones=(),
        uitkomsten_per_zone=(),
        energie=None,
        uitstoot=None,
        versie_modelgegevens=versie,
        waarschuwingen=tuple(waarschuwingen),
        overgeslagen=True,
        reden=reden,
    )



def _bereken_bericht(
    bericht: Bericht,
    gesprek: Gesprek,
    config: BerekenConfig,
    versie: str,
) -> BerichtBerekening:
    """Reken één assistant-bericht door volgens de rekenstap uit de spec."""
    tokens = schat_tokens(bericht.inhoud)
    niet_westers = is_niet_westers(bericht.inhoud)
    attributie = bepaal_model(bericht, gesprek, config)
    latency = config.request_latency if config.request_latency is not None else math.inf
    latency_aangenomen = config.request_latency is None
    waarschuwingen: list[str] = []
    rekenmodel: str
    if attributie == ONBEKEND_MODEL:
        val = config.provider_standaard_modellen.get(gesprek.provider)
        bron = "provider-standaardmodel"
        if val is None:
            val = config.fallback_model
            bron = "fallback-model"
        if val is None:
            val = STANDAARD_PROVIDER_MODELLEN.get(gesprek.provider)
            bron = "standaard-basismodel uit de config"
        if val is None:
            reden = "model onbekend en geen fallback of provider-default ingesteld"
            waarschuwingen.append(reden)
            return _overgeslagen_bericht(
                bericht, attributie, tokens, niet_westers, versie, reden, waarschuwingen
            )
        rekenmodel = val
        waarschuwingen.append(f"attributie 'onbekend', {bron} '{val}' gebruikt")
    else:
        rekenmodel = attributie
    zones = bepaal_zones(gesprek.provider, config.zones_per_provider)
    per_zone: list[ZoneUitkomst] = []
    for zone in zones:
        try:
            uitkomst = schat_impact(gesprek.provider, rekenmodel, tokens, zone, latency)
        except ModelOnbekendBijEcoLogits as fout:
            return _overgeslagen_bericht(
                bericht, attributie, tokens, niet_westers, versie, str(fout), waarschuwingen
            )
        per_zone.append(
            ZoneUitkomst(zone=zone, energie=uitkomst.energie, uitstoot=uitkomst.uitstoot)
        )
        waarschuwingen.extend(uitkomst.waarschuwingen)
    energie = _bandbreedte(tuple(zone_uit.energie for zone_uit in per_zone))
    uitstoot = _bandbreedte(tuple(zone_uit.uitstoot for zone_uit in per_zone))
    return BerichtBerekening(
        bericht_id=bericht.id,
        attributie=attributie,
        model=rekenmodel,
        tokens=tokens,
        niet_westers=niet_westers,
        latency=latency,
        latency_aangenomen=latency_aangenomen,
        zones=zones,
        uitkomsten_per_zone=tuple(per_zone),
        energie=energie,
        uitstoot=uitstoot,
        versie_modelgegevens=versie,
        waarschuwingen=tuple(waarschuwingen),
        overgeslagen=False,
        reden=None,
    )


def bereken_gesprek(
    gesprek: Gesprek, config: BerekenConfig | None = None
) -> GesprekBerekening:
    """Bereken de impact voor alle assistant-berichten van één gesprek.

    Args:
        gesprek: een gesprek uit het canonieke model.
        config: de berekeningsconfiguratie; de default gebruikt WOR en telt
            onbekende modellen niet mee (FR-5, FR-7).

    Returns:
        De berekening per bericht plus de totaalsommen van het gesprek.
    """
    config = config if config is not None else BerekenConfig()
    versie = ecologits.__version__
    berichten = tuple(
        _bereken_bericht(bericht, gesprek, config, versie)
        for bericht in gesprek.berichten
        if bericht.rol == "assistant"
    )
    meetellende_energie = [b.energie for b in berichten if b.energie is not None]
    meetellende_uitstoot = [b.uitstoot for b in berichten if b.uitstoot is not None]
    return GesprekBerekening(
        gesprek_id=gesprek.id,
        provider=gesprek.provider,
        berichten=berichten,
        totale_energie=_tel_op(meetellende_energie),
        totale_uitstoot=_tel_op(meetellende_uitstoot),
        totaal_tokens=sum(b.tokens for b in berichten),
        aantal_overgeslagen=sum(1 for b in berichten if b.overgeslagen),
        aantal_onbekend_model=sum(
            1 for b in berichten if b.attributie == ONBEKEND_MODEL
        ),
        aantal_niet_westers=sum(1 for b in berichten if b.niet_westers),
    )


def bereken_gesprekken(
    gesprekken: list[Gesprek], config: BerekenConfig | None = None
) -> BerekeningRapport:
    """Bereken de impact voor alle gesprekken van een export.

    Args:
        gesprekken: de gesprekken uit het canonieke model.
        config: de berekeningsconfiguratie.

    Returns:
        Het totale rapport met de totaalsommen over alle berichten.
    """
    config = config if config is not None else BerekenConfig()
    verwerkt = tuple(bereken_gesprek(gesprek, config) for gesprek in gesprekken)
    alle_berichten = [bericht for gesprek in verwerkt for bericht in gesprek.berichten]
    meetellende_energie = [b.energie for b in alle_berichten if b.energie is not None]
    meetellende_uitstoot = [b.uitstoot for b in alle_berichten if b.uitstoot is not None]
    waarschuwingen: list[str] = []
    if config.request_latency is None:
        waarschuwingen.append(
            "geen request-latency gemeten: de vaste default van EcoLogits is "
            "gebruikt (A4), het resultaat is daardoor breder dan bij een "
            "gemeten latency"
        )
    return BerekeningRapport(
        versie_modelgegevens=ecologits.__version__,
        versie_module=_moduleversie(),
        aantal_berichten=len(alle_berichten),
        aantal_overgeslagen=sum(1 for b in alle_berichten if b.overgeslagen),
        aantal_onbekend_model=sum(
            1 for b in alle_berichten if b.attributie == ONBEKEND_MODEL
        ),
        aantal_niet_westers=sum(1 for b in alle_berichten if b.niet_westers),
        totaal_tokens=sum(b.tokens for b in alle_berichten),
        totale_energie=_tel_op(meetellende_energie),
        totale_uitstoot=_tel_op(meetellende_uitstoot),
        gesprekken=verwerkt,
        waarschuwingen=tuple(waarschuwingen),
    )
