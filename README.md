# SustainableAI-CarbonFootprint

Tooling om de carbon footprint van AI-gebruik te meten via chat exports van
aanbieders zoals OpenAI en Mistral.

Dit project is opgebouwd uit modules die elk een eigen spec in `specs/` volgen.
Module 1 (`structuur_detectie`), module 2 (`carbon_calculator`), module 3
(`bulk_analyser`) en de CLI (`cli`) zijn geïmplementeerd en worden in deze
README beschreven.

## Module 1: structuurdetectie en parsing

De module herkent automatisch de aanbieder en het formaat van een onbekende
chat export, leest de berichten in en normaliseert ze naar één canoniek model.
Je hoeft niet op voorhand te zeggen waar de data vandaan komt.

Ondersteunde formats (v1):

- openai: een bestand `conversations.json` met een mapping-boom uit `parent`
  en `children`. Alleen het actieve pad van de wortel tot `current_node` wordt
  opgenomen (aanname A1 uit de spec).
- mistral: een map `chat-export-<timestamp>/` met één `chat-<uuid>.json` per
  gesprek.

### Canoniek model

Elke parser levert een lijst van `Gesprek` objecten. Een gesprek heeft:

- `id`: string, verplicht.
- `titel`: string of `None`.
- `provider`: bijvoorbeeld `"openai"` of `"mistral"`.
- `created_at`: tijdstip (epoch seconden of ISO 8601) of `None`.
- `berichten`: chronologisch gesorteerde lijst van `Bericht` objecten.

Een bericht heeft:

- `id`: string of `None`.
- `rol`: `"user"`, `"assistant"`, `"system"` of `"tool"`.
- `inhoud`: de samengevoegde tekstdelen van de bron.
- `created_at`: tijdstip of `None`.
- `model`: string of `None` als onbekend.

## Installatie

Vereisten: Python 3.12 of nieuwer en [uv](https://docs.astral.sh/uv/).

Installeer de project-packages én de dev-tools in de lokale omgeving:

```bash
uv sync --extra dev
```

Dat doet twee dingen:

- `uv sync` installeert het project zelf plus de runtime-dependencies
  (`ecologits`) in een virtuele omgeving onder `./.venv`.
- `--extra dev` voegt daar de dev-tools aan toe die de harness nodig heeft:
  `pytest`, `mypy` en `ruff`, plus `tiktoken` (alleen voor de
  tokenschattingsreferentie in de tests).

Er is dus geen globale installatie van pytest, mypy of ruff nodig; alles zit
in `./.venv`. Werk je met een andere Python-versie of een aparte locatie, dan
kan dat via `uv sync --extra dev --python 3.12` of `--python 3.13`.

De module `structuur_detectie` heeft geen runtime dependencies, alleen de
standaardbibliotheek. Module 2 gebruikt EcoLogits als enige
runtime-dependency (zie hieronder).

## Commando's uitvoeren met uv

De dev-tools staan in `./.venv/bin`, niet globaal. Roep ze daarom met
`uv run` aan, dat voert het commando uit binnen de projectomgeving:

```bash
uv run python -c "import structuur_detectie, carbon_calculator; print('ok')"
uv run pytest tests/
uv run mypy .
uv run ruff check .
```

De harness `./harness/run_tests.sh` zoekt de tools via `command -v`, dus die
moeten op het `PATH` staan. Twee manieren om dat te regelen:

```bash
# optie 1: de virtuele omgeving activeren, daarna gewoon de harness draaien
source .venv/bin/activate
./harness/run_tests.sh

# optie 2: .venv/bin tijdelijk op het PATH zetten
PATH="$PWD/.venv/bin:$PATH" ./harness/run_tests.sh
```

## Gebruik

Detecteer de provider van een export:

```python
from structuur_detectie import detecteer

print(detecteer("pad/naar/export"))  # "openai" of "mistral"
```

Parse een export naar het canonieke model:

```python
from structuur_detectie import parseer

gesprekken = parseer("pad/naar/export")
for gesprek in gesprekken:
    print(gesprek.id, gesprek.provider, gesprek.titel, len(gesprek.berichten))
    for bericht in gesprek.berichten:
        print(bericht.rol, bericht.model, bericht.inhoud)
```

De input is een map of een bestand:

```python
parseer("conversations.json")                          # openai
parseer("chat-export-1700000000000")                   # mistral
parseer("chat-export-1700000000000/chat-1....json")    # mistral, één gesprek
```

`Gesprek` en `Bericht` hebben ook een `naar_dict()` methode voor JSON-output:

```python
import json

rapport = [gesprek.naar_dict() for gesprek in gesprekken]
print(json.dumps(rapport, indent=2))
```

### Eigen parser toevoegen (extensiepunt FR-7)

Een nieuwe parser wordt geregistreerd in een registry met een kenmerkscore en
een parse-functie. De detector hoeft niet te worden aangepast.

```python
from pathlib import Path
from structuur_detectie import Gesprek, Parser, Registry

def scoort(bron: Path) -> float:
    return 10.0 if bron.name == "speciale_export.json" else 0.0

def parse(bron: Path) -> list[Gesprek]:
    return [Gesprek(id="spec-1", titel=None, provider="speciaal",
                    created_at=None, berichten=[])]

registry = Registry()
registry.registreer(Parser(provider="speciaal", naam="speciaal",
                           scoort=scoort, parse=parse))
print(registry.detecteer("speciale_export.json"))  # "speciaal"
```

De detector sorteert de kandidaten op score en probeert ze op volgorde. De
eerste parser die succesvol parseert wint.

### Fouten

- `ParseFout`: de input voldeed niet aan het verwachte exportformaat.
- `OnbekendFormaatError`: geen enkele geregistreerde parser herkende de export.
  De melding noemt de gevonden bestandsnamen en JSON-sleutels, met suggesties.

## Module 2: carbon calculator

De calculator schat per assistant-bericht de energie (kWh) en uitstoot
(kg CO2eq) van een modelantwoord, met EcoLogits als rekenkern. De belangrijkste
keuzes staan in `docs/ADR/carbon-calculator.md`.

De module rekent op het canonieke model van module 1:

```python
from carbon_calculator import bereken_gesprekken
from structuur_detectie import parseer

gesprekken = parseer("pad/naar/export")
rapport = bereken_gesprekken(gesprekken)
print(rapport.totale_energie)   # laag, hoog, gemiddelde in kWh
print(rapport.totale_uitstoot)  # laag, hoog, gemiddelde in kg CO2eq
print(rapport.aantal_overgeslagen, rapport.aantal_onbekend_model)
```

Elke berekening draait voor minstens twee elektriciteitsmix-zones (FR-6), met
`WOR` als default. Zonkeuzes en andere opties gaan via `BerekenConfig`:

```python
from carbon_calculator import BerekenConfig, bereken_gesprekken

config = BerekenConfig(
    zones_per_provider={"openai": "USA", "mistral": "EEE"},
    provider_standaard_modellen={"mistral": "mistral-large-2512"},
    fallback_model="gpt-4o-mini",
)
rapport = bereken_gesprekken(gesprekken, config)
```

- modellen waarvan de attributie `onbekend` is leveren een waarschuwing en
  tellen via de provider-default, het fallback-model of het standaard
  basismodel uit de config (FR-7);
- berichten met veel niet-westerse tekens worden gemarkeerd (FR-8) en langere
  tokenhoeveelheden worden daarop niet vertrouwd;
- een ongeldige zone geeft een duidelijke fout (FR-5).

#### Standaard basismodel per provider

Mistral-exports bevatten nooit modelinformatie, daarom voorziet de config daar
standaard in. Het basismodel per provider staat in `STANDAARD_PROVIDER_MODELLEN`
in `src/carbon_calculator/config.py` en is ook geëxporteerd uit
`carbon_calculator`:

```python
from carbon_calculator import STANDAARD_PROVIDER_MODELLEN

print(STANDAARD_PROVIDER_MODELLEN)  # {'mistral': 'mistral-large-2512'}
```

De volgorde in de berekening voor een bericht met attributie `onbekend` is:
het expliciete provider-standaardmodel (`--model`), dan het globale
fallback-model (`--fallback-model`), dan het standaard basismodel uit de
config. Expliciete configuratie wint dus altijd van de default. Een bericht
wordt alleen overgeslagen als geen van de drie een model oplevert dat EcoLogits
voor die provider kent.

## Module 3: bulk analyser

De bulk analyser (pijplijn uit `specs/spec_bulk_analyser.md`) neemt een chat
export (map, bestand of zip) in, herkent automatisch de aanbieder en het
formaat, berekent per assistant-bericht de impact en produceert een
begrijpelijk rapport per model, per maand, per gesprek en per provider. De
hele berekening draait lokaal, zonder netwerkverkeer (NFR-1).

```python
from bulk_analyser import analyseer, genereeer_json, genereeer_markdown
from carbon_calculator import BerekenConfig

rapport = analyseer(
    "pad/naar/export",                       # map, bestand of .zip
    BerekenConfig(provider_standaard_modellen={"mistral": "mistral-large-2512"}),
)
print(rapport.herkende_aanbieder, rapport.aantal_gesprekken)
print(genereeer_json(rapport))               # machineleesbaar
print(genereeer_markdown(rapport))           # mensleesbaar, sectie 'methode en bronnen'
```

De aggregaten zijn terug te vinden in `rapport.aggregaten` (`.totaal`,
`.per_model`, `.per_maand`, `.per_gesprek`, `.per_provider`). Overgeslagen
berichten staan expliciet met een reden in `rapport.overgeslagen` (NFR-5).

### Demo op de echte voorbeelden

```bash
uv run python - <<'PY'
from bulk_analyser import analyseer, genereeer_markdown
from carbon_calculator import BerekenConfig

rapport = analyseer(
    "context/example_data_dump/mistral/chat-export-1793108657334",
    BerekenConfig(provider_standaard_modellen={"mistral": "mistral-large-2512"}),
)
print(genereeer_markdown(rapport))
PY
```

De mistral-voorbeelden staan in `context/example_data_dump/`. Een
openai-export wordt op dezelfde manier geanalyseerd met een
`conversations.json`-bestand (zie de synthetische fixture in `tests/fixtures/`).

## CLI: co2chat

De CLI is een lichtgewicht commandline-interface die de bulk-pijplijn
blootstelt voor gebruik vanaf de terminal. Hij bevat geen eigen reken- of
aggregatielogica (NFR-5 uit `specs/spec_cli.md`): hij roept alleen de
bestaande modules aan (`analyseer`, `genereeer_json`, `genereeer_markdown`)
en verzorgt de invoer, de uitvoer en de foutafhandeling.

Na `uv sync --extra dev` staat het commando `co2chat` in `./.venv/bin`, dus op
het PATH zodra de virtuele omgeving geactiveerd is (zie 'Commando's uitvoeren
met uv').

### Voorbeelden

Een analyse starten en het markdown-rapport naar de terminal printen:

```bash
co2chat context/example_data_dump/mistral/chat-export-1793108657334
```

Meteen JSON in een bestand schrijven:

```bash
co2chat export.zip --json -o rapport.json
```

Een provider-default model en een elektriciteitsmix-zone meegeven:

```bash
co2chat export/ --model mistral-large-2512 --zone EEE
```

### Opties

| optie | omschrijving | default |
|---|---|---|
| `bron` | pad naar een map, bestand of `.zip` van een chat export (verplicht) | - |
| `-j`, `--json` | schrijf het rapport als JSON naar de uitvoer | markdown |
| `--markdown` | schrijf als markdown (expliciet) | ja |
| `-o`, `--output PAD` | schrijf naar een bestand in plaats van stdout; het formaat volgt de extensie (`.json`/`.md`) of een expliciete vlag | stdout |
| `--zone ZONE` | elektriciteitsmix-zone voor alle providers (bijvoorbeeld `WOR`, `EEE`, `USA`) | `WOR` (default van de calculator) |
| `--model MODEL` | standaardmodel voor providers zonder modelinformatie | geen |
| `--fallback-model MODEL` | fallback-model voor berichten met attributie `onbekend` | geen |
| `-V`, `--version` | print de versie en stop | - |
| `-h`, `--help` | toon de help-tekst | - |

`--json` en `--markdown` sluiten elkaar uit. `--zone` en `--model` vullen de
`BerekenConfig` voor elke gedetecteerde aanbieder (FR-4); `--fallback-model`
is globaal. Zonder deze vlaggen geldt de default van de calculator: die bevat
voor mistral het standaard basismodel uit `STANDAARD_PROVIDER_MODELLEN`
(`src/carbon_calculator/config.py`), zodat ook mistral-exports zonder extra
vlag worden berekend in plaats van overgeslagen.

### Exitcodes

- `0`: de analyse slaagt en het rapport wordt geschreven.
- `1`: een fout uit de modules (bijvoorbeeld `AnalyseFout`,
  `OnbekendFormaatError` of `OngeldigeZoneError`) of een I/O-fout bij het
  schrijven. De CLI print de melding op stderr, zonder traceback.
- `2`: een gebruikersfout in de commandoregel (argparse), zoals een
  ontbrekende `bron` of een onbekende optie.

De analyse draait volledig lokaal; de CLI zelf doet geen netwerkverkeer
(NFR-2).

## Testen

Zorg eerst dat de packages en dev-tools geïnstalleerd zijn (zie
'Installatie'), daarna:

```bash
./harness/run_tests.sh
```

De harness draait ruff (lint), mypy (type check, strict) en pytest. Exit code 0
betekent dat alles slaagt. De tools moeten op het `PATH` staan; zie
'Commando's uitvoeren met uv' voor de twee manieren om dat te regelen. Je kunt
de onderdelen ook los draaien:

```bash
uv run pytest tests/   # alleen de tests
uv run mypy .          # alleen de type check
uv run ruff check .    # alleen de lint
```

Tip: de referentietest voor de tokenschatting gebruikt tiktoken. De eerste
keer dat je die test draait downloadt tiktoken de tokenizer-vocab
(`cl100k_base`); dat is test-only en gebeurt alleen bij de eerste run.

Tests en synthetische fixtures staan in `tests/`; de echte mistral-voorbeelden
staan in `context/example_data_dump/`.

## Verdere documentatie

- `specs/spec_structuur_detectie.md`: de modulespec met alle vereisten.
- `specs/spec_bulk_analyser.md`: de pijplijn waar deze module in past.
- `specs/spec_cli.md`: de CLI-spec met alle vereisten.
- `docs/ADR/`: architectuurbeslissingen.
- `improvements.md`: verbetersuggesties tijdens het werk.
