# Spec: structuur detectie en parsing van chat exports

## Doel

Deze module herkent automatisch de aanbieder en het formaat van een onbekende
chat export, leest de berichten in en normaliseert ze naar één canoniek model.
De gebruiker hoeft niet op voorhand te zeggen waar de data vandaan komt.
Andere modules (carbon calculator, bulk analyser) draaien alleen op het
canonieke model.

Deze spec hoort bij de bulk analyser uit `specs/spec_bulk_analyser.md`.

## Definities en concepten

- export: een bestand of map met chatgeschiedenis van een aanbieder.
- aanbieder (provider): bijvoorbeeld OpenAI of Mistral.
- formaat: de concrete bestands- en JSON-structuur van een export.
- detector: bepaalt welke parser bij de input past.
- parser: leest één bekend formaat en bouwt het canonieke model.
- canoniek model: het neutrale tussenmodel dat elke parser als output levert.

## Canoniek model

Output van elke parser, als een lijst van gesprekken.

Gesprek:
- id: string, verplicht.
- titel: string of null.
- provider: string (bijvoorbeeld "openai" of "mistral").
- created_at: tijdstip (epoch seconden of ISO 8601) of null.
- berichten: lijst van berichten, chronologisch gesorteerd.

Bericht:
- id: string of null.
- rol: "user", "assistant", "system" of "tool".
- inhoud: tekst (de samengevoegde parts van de bron).
- created_at: tijdstip of null.
- model: string of null als onbekend.

JSON-voorbeeld:

    [
      {
        "id": "conv-1",
        "titel": "Voorbeeld",
        "provider": "openai",
        "created_at": 1733294339.556244,
        "berichten": [
          {"id": "m1", "rol": "user", "inhoud": "Hallo", "created_at": 1733294335.0, "model": null},
          {"id": "m2", "rol": "assistant", "inhoud": "Hoi", "created_at": 1733294339.5, "model": "gpt-4o"}
        ]
      }
    ]

Toelichting:
- niet elke aanbieder ondersteunt vertakkingen in een gesprek, daarom bevat het
  canonieke model geen boodschappenboom.
- de boom van OpenAI wordt afgeplat tot het actieve pad volgens `current_node`
  (zie aanname A1).
- het canonieke model is de enige interface tussen modules.

## Ondersteunde formats in v1

- openai: `conversations.json` met een mapping-boom uit `parent` en `children`,
  met `current_node` als actieve tak en `model_slug` in de metadata van
  assistant-berichten.
- mistral: map `chat-export-<timestamp>/` met één `chat-<uuid>.json` per
  gesprek. Elk bestand is een array van berichten met `role`, `content` en
  `createdAt`. Er is geen modelveld en geen titel in dit formaat.

Beide structuren zijn geverifieerd met echte exports: de mistral-voorbeelden
staan in `context/example_data_dump/`, de openai-structuur is geverifieerd
tegen een export-voorbeeld uit december 2024 (repo `sanand0/openai-conversations`).

## Detectiemethode

De detector onderzoekt de input en kiest een parser:

1. geef elke kandidaat-parser een score op basis van kenmerken, bijvoorbeeld
   bestandsnamen (`conversations.json`, `chat-*.json`, `chat-export-*`) en
   JSON-sleutelpatronen (aanwezigheid van `mapping` plus `current_node`, of
   `role` plus `createdAt`).
2. probeer de kandidaten in volgorde van score; de eerste parser die succesvol
   valideert en parseert wint.
3. slaagt geen enkele kandidaat: geef een duidelijke fout met de gevonden
   kenmerken en suggesties (FR-8).

De detectie draait volledig lokaal en stuurt geen data naar buiten (NFR-1).

## Functionele vereisten

- FR-1 detectie: bij een geldige export van een bekend formaat wordt de juiste
  aanbieder en het juiste formaat gekozen. Acceptatie: `openai` en `mistral`
  worden herkend door hun kenmerken, zonder gebruikersinput.
- FR-2 canonieke output: elke parser levert uitsluitend het canonieke model uit
  'Canoniek model'. Acceptatie: alle velden aanwezig, geen provider-eigen velden.
- FR-3 rollen en inhoud: rollen worden vertaald naar `user`, `assistant`,
  `system` of `tool` en de delen van een bericht worden samengevoegd tot één
  tekst. Acceptatie: een openai-bericht met meerdere `parts` geeft één inhoud.
- FR-4 actief pad: bij een openai-export wordt alleen het pad van de wortel tot
  `current_node` opgenomen. Acceptatie: vertakkingen die niet op het actieve
  pad liggen ontbreken in de output.
- FR-5 modelattributie: waar de bron een model vermeldt (`model_slug`), komt
  dat in het canonieke model. Acceptatie: mistral-berichten krijgen altijd
  `model: null`.
- FR-6 ordening: berichten zijn chronologisch per gesprek. Acceptatie:
  gesorteerd op `created_at`, stabiel bij onbekende tijden.
- FR-7 extensiepunt: een nieuwe parser wordt geregistreerd in een registry met
  een kenmerkscore en een parse-functie, zonder wijziging aan de detector.
  Acceptatie: een test-parser in de registry wordt gevonden en gebruikt.
- FR-8 onbekende input: een export die geen enkele parser herkent geeft een
  fout met de gevonden kenmerken. Acceptatie: de foutmelding noemt minimaal de
  bestandsnamen en de gevonden JSON-sleutels.

## Niet-functionele vereisten

- NFR-1 privacy: alle detectie en parsing gebeurt lokaal, zonder netwerkverkeer.
- NFR-2 prestaties: een export van een jaar (orde 1000 gesprekken) wordt
  binnen 2 minuten gedetecteerd en geparseerd op reguliere hardware.
- NFR-3 afhankelijkheden: alleen de standaardbibliotheek, geen externe libraries.
- NFR-4 kwaliteit: Python 3.12+, type hints, Google-style docstrings, pytest,
  geen ongebruikte imports of variabelen.

## Randvoorwaarden en aannames

- A1 afplatting van de boom: alleen het actieve pad van de wortel naar
  `current_node` telt mee; niet-gekozen takken worden bewust weggelaten.
- A2 elk gesprek in de output vermeldt de provider.
- A3 nieuwe formats worden toegevoegd via de registry en hun kenmerkscore;
  de detector zelf hoeft dan niet te worden herschreven (FR-7).
- A4 de echte exports in `context/example_data_dump/` dienen als
  ontwikkel- en integratiedata; de fixtures in `tests/` zijn synthetisch en klein.

## Open punten (voor overleg)

1. welke aanbieders komen na OpenAI en Mistral (bijvoorbeeld Claude, Gemini of
   Copilot) en hoe urgent is dat voor de demo.
2. ondersteunen we naast een map ook een zip en een export die meerdere
   aanbieders bevat.
3. willen we een handmatige override (de gebruiker kiest de parser als detectie
   faalt of twijfelt).

## Milestones en Definition of Done

Milestone M1a: parsers voor openai en mistral plus het canonieke model, met
tests op synthetische fixtures. Acceptatie: de parsers slagen op de echte
voorbeelden in `context/example_data_dump/` (mistral) en op een synthetische
openai-`conversations.json`.

Milestone M1b: de registry en de detector met kenmerkenscores, inclusief de
foutafhandeling voor onbekende input.

Definition of Done:
- alle FRs en NFRs van de milestones hebben tests die slagen.
- `harness/run_tests.sh` geeft exit code 0, mypy en ruff geven geen fouten.
- de output van beide parsers voldoet aan het canonieke model (FR-2).
- verbetersuggesties tijdens het werk staan in `improvements.md`.

