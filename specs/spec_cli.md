# Spec: commandline interface voor bulk analyse

## Doel

Een erg lichtgewicht CLI die de bestaande bulk-pijplijn (`bulk_analyser`)
blootstelt voor gebruik vanaf de terminal. De CLI bevat geen eigen reken- of
aggregatielogica, hij roept alleen de bestaande modules aan en verzorgt de
invoer, de uitvoer (JSON of markdown) en de foutafhandeling.

Deze spec beschrijft de CLI alleen; de onderliggende modules volgen hun eigen
specs:

- `specs/spec_structuur_detectie.md` voor detectie en parsing (module 1).
- `specs/spec_carbon_calculator.md` voor de berekening (module 2).
- `specs/spec_bulk_analyser.md` voor de pijplijn, aggregatie en rapportage.

## Gebruik

Een analyse starten en het markdown-rapport naar de terminal printen:

    co2chat context/example_data_dump/mistral/chat-export-1793108657334

Meteen JSON in een bestand schrijven:

    co2chat export.zip --json -o rapport.json

Een provider-default model en een elektriciteitsmix-zone meegeven:

    co2chat export/ --model mistral-large-2512 --zone EEE

## Commando en opties

| positie | optie | omschrijving | default |
|---|---|---|---|
| positioneel | `bron` | pad naar een map, bestand of `.zip` van een chat export (verplicht) | - |
| | `-j`, `--json` | schrijf het rapport als JSON naar de uitvoer | markdown |
| | `--markdown` | schrijf als markdown (expliciet) | ja |
| | `-o`, `--output PAD` | schrijf naar een bestand in plaats van stdout; het formaat volgt de extensie (`.json`/`.md`) of een expliciete vlag | stdout |
| | `--zone ZONE` | elektriciteitsmix-zone voor alle providers (bijvoorbeeld `WOR`, `EEE`, `USA`) | `WOR` (default van de calculator) |
| | `--model MODEL` | standaardmodel voor providers zonder modelinformatie (bijvoorbeeld mistral) | geen |
| | `--fallback-model MODEL` | fallback-model voor berichten met attributie `onbekend` | geen |
| | `-V`, `--version` | print de versie en stop, exit 0 | - |
| | `-h`, `--help` | toon de help-tekst | - |

`--json` en `--markdown` sluiten elkaar uit; argparse-vragen dat af.

## Config doorgeven (FR-4)

`--zone` vult `zones_per_provider` in de `BerekenConfig` voor elke gedetecteerde
provider. `--model` vult `provider_standaard_modellen` voor elke provider,
`--fallback-model` vult `fallback_model`. Zonder deze vlaggen geldt de default
van de calculator, exact zoals de pijplijn die los aanroept: `WOR` als zone en
voor mistral het standaard basismodel uit `STANDAARD_PROVIDER_MODELLEN`
(`src/carbon_calculator/config.py`), zodat mistral-berichten zonder model
standaard meetellen in plaats van worden overgeslagen (FR-7).

De opties bepalen de output en de config, nooit de logica. De CLI is dus een
dunne wrapper om `analyseer`, `genereeer_json` en `genereeer_markdown`.

## Foutafhandeling en exitcodes (FR-5, FR-6)

- exit 0: de analyse slaagt en het rapport wordt geschreven.
- exit 1: een fout uit de modules (bijvoorbeeld `AnalyseFout`,
  `OnbekendFormaatError` of `OngeldigeZoneError`) of een I/O-fout bij het
  schrijven. De CLI print de melding op stderr, zonder traceback.
- exit 2: een gebruikersfout in de commandoregel (argparse-default), zoals een
  ontbrekende `bron` of onbekende optie.

## Functionele vereisten

- FR-1 basis: `co2chat bron` analyseert de export en print het markdown-rapport
  naar stdout. Acceptatie: de output bevat de sectie 'methode en bronnen' en
  eindigt met exit 0.
- FR-2 JSON: met `--json` is de output het JSON-rapport. Acceptatie: de JSON
  is geldig en bevat alle aggregaten, identiek aan `genereeer_json`.
- FR-3 bestand: met `--output PAD` gaat de output naar het bestand en niet naar
  stdout; het formaat volgt de extensie of een expliciete vlag. Acceptatie: een
  bestaand bestand wordt overschreven en bevat het juiste formaat.
- FR-4 config: `--zone`, `--model` en `--fallback-model` worden doorgegeven aan
  `BerekenConfig`. Acceptatie: zonder vlaggen is de config gelijk aan de
  default; met vlaggen staan de waarden in het rapport (zones, modellen).
- FR-5 fouten: een ongeldige export of ongeldige config geeft exit 1 met de
  melding op stderr en geen traceback. Acceptatie: een niet-bestaand pad en een
  ongeldige zone leveren exit 1 met een duidelijke boodschap.
- FR-6 exitcodes: gebruikersfouten in de commandoregel geven exit 2. Acceptatie:
  `co2chat` zonder argumenten en `co2chat --onbekende-optie` geven exit 2.

## Niet-functionele vereisten

- NFR-1 afhankelijkheden: alleen de standaardbibliotheek (`argparse`, `sys`,
  `json`, `pathlib`) bovenop de bestaande projectmodules; geen nieuwe
  dependencies.
- NFR-2 privacy: de CLI zelf doet geen netwerkverkeer; de analyse draait
  volledig lokaal (zie de designspecs).
- NFR-3 determinisme: dezelfde input met dezelfde vlaggen geeft dezelfde
  output. Acceptatie: twee runs op dezelfde export geven identieke output.
- NFR-4 kwaliteit: Python 3.12+, type hints, Google-style docstrings, pytest,
  geen ongebruikte imports of variabelen. De CLI draait door de harness.
- NFR-5 enkele bron van waarheid: de CLI bevat geen eigen reken- of
  aggregatielogica. Acceptatie: de CLI-uitspraken zijn gelijk aan een directe
  aanroep van de modules.

## Randvoorwaarden en aannames

- A1 de CLI roept de pijplijn aan met `analyseer(bron, config)` en gebruikt de
  bestaande rapportage-functies; er komt geen nieuw formatteringspad.
- A2 de invoer is één export; `bron` kan een map, bestand of `.zip` zijn,
  precies zoals `analyseer` die als ondersteunt.
- A3 zolang de modules de enige interface zijn, hoeft de CLI niet te veranderen
  bij nieuwe providers of formats (via de registry van module 1).

## Milestones

- M1: de argparse-vlaggen en de mapper van vlaggen naar `BerekenConfig`, met
  tests voor FR-1, FR-2, FR-4 en FR-6.
- M2: de foutafhandeling (stderr, exit 1) en het schrijven naar bestand, met
  tests voor FR-3 en FR-5.

## Definition of Done

- alle vereisten (FR en NFR) van de milestones hebben tests die slagen.
- `harness/run_tests.sh` geeft exit code 0; mypy en ruff geven geen fouten.
- de CLI is geregistreerd als console-script in `pyproject.toml`, zodat
  `co2chat` na installatie op het PATH staat.
- de demo draait op de echte voorbeelden uit `context/example_data_dump/`
  (mistral) en op een openai-`conversations.json`.
- verbetersuggesties tijdens het werk staan in `improvements.md`.