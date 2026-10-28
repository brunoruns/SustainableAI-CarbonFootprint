# Spec: bulk analyser voor chat exports

## Doel

De hoofdpijplijn van de bulk mode: een export innemen, automatisch herkennen
en normaliseren, per bericht de uitstoot berekenen en een begrijpelijk rapport
produceren per model, per maand en per gesprek.

Deze spec beschrijft wat de modulespecs niet beschrijven: de orkestratie,
de aggregatie en de rapportage. De modulespecificaties zijn:

- `specs/spec_structuur_detectie.md` voor detectie en parsing (module 1).
- `specs/spec_carbon_calculator.md` voor de energie- en uitstootberekening
  via EcoLogits (module 2).

## Pijplijn

1. invoer innemen: een zip of een map met de export.
2. uitpakken (alleen bij zip) en de bestanden verzamelen.
3. detecteren: aanbieder en formaat herkennen (module 1).
4. parsen: normaliseren naar het canonieke model (module 1).
5. berekenen: per assistant-bericht energie en uitstoot schatten (module 2).
6. aggregeren: totalen per model, per maand (UTC) en per gesprek.
7. rapporteren: JSON en markdown, met methode en bron.

Elke stap kan falen; een fout is duidelijk en wijst de gebruiker naar de
oorzaak en de stap (FR-5).

## Aggregatie (stap 6)

- per model: tokens, requests, kWh, kg CO2eq en het aandeel onbekende modellen.
- per maand (UTC): dezelfde totalen, op basis van `created_at` van het bericht.
- per gesprek: dezelfde totalen plus titel en provider.
- algemeen totaal over de hele export.
- deelgroepen tellen op tot het totaal binnen de afrondingsmarge (FR-2).
- bij een export met meerdere aanbieders worden de totalen ook per provider
  getoond.

## Rapport (stap 7)

- JSON: machineleesbaar, reproduceerbaar, met alle aggregaten uit
  'Aggregatie'.
- markdown: mensleesbaar, met een sectie 'methode en bronnen' met:
  - de herkende aanbieder en het herkende formaat;
  - de tokenschattingsmethode;
  - de rekenkern (EcoLogits) en de gebruikte versie van de modelgegevens;
  - de aangenomen elektriciteitsmix-zones en de laag-hoog bandbreedte;
  - het aantal berichten zonder model en het aantal overgeslagen berichten;
  - een bronverwijzing bij elk cijfer.

## Functionele vereisten

- FR-1 end-to-end: een geldige export levert een volledig rapport in JSON en
  markdown. Acceptatie: identieke input met dezelfde configuratie geeft
  identieke output.
- FR-2 aggregatie: de som van de deelgroepen is gelijk aan het totaal binnen
  de afrondingsmarge. Acceptatie: de controlesom in de tests is gelijk.
- FR-3 rapportvelden: alle aggregaten uit 'Aggregatie' zijn aanwezig, plus het
  aantal gesprekken en het aantal berichten. Acceptatie: het JSON-schema test
  elk veld.
- FR-4 transparantie: het rapport bevat de sectie 'methode en bronnen' uit
  'Rapport'. Acceptatie: elke sectie uit de opsomming staat in de markdown.
- FR-5 fouten: ongeldige input geeft een duidelijke foutmelding met de stap en
  de oorzaak. Acceptatie: geen crash en geen stil verkeerde output, ook niet
  bij een lege export of een ontbrekende map.
- FR-6 provider: elk gesprek en elk aggregaat vermeldt de provider. Acceptatie:
  de output van een synthetische gemengde export groepeert per provider.

## Niet-functionele vereisten

- NFR-1 privacy: de verwerking gebeurt volledig lokaal; de export verlaat het
  apparaat niet en er is geen extern netwerkverkeer (zie ook de calculator-spec).
- NFR-2 prestaties: een export van een jaar (orde 1000 gesprekken) wordt
  binnen 5 minuten verwerkt op reguliere hardware.
- NFR-3 afhankelijkheden: minimale external libraries, `ecologits` is de enige
  runtime-dependency van de berekening; geen eigen rekenlogica.
- NFR-4 kwaliteit: Python 3.12+, type hints, Google-style docstrings, pytest,
  geen ongebruikte imports of variabelen.
- NFR-5 volledigheid: elk bericht dat niet berekend kan worden staat expliciet
  in het rapport (met reden), nooit stil weggelaten.

## Randvoorwaarden en aannames

- A1 v1 ondersteunt exports van OpenAI en Mistral; andere aanbieders volgen via
  de registry van module 1 zonder wijziging aan de pijplijn.
- A2 de maandindeling is UTC.
- A3 het rapport is de primaire output; de web UI is een latere spec (via
  `docs/ADR/PRD.md`).
- A4 de demo draait op de echte voorbeelden uit `context/example_data_dump/`.

## Milestones

- M1: module 1 (detectie en parsing) met tests, zie
  `specs/spec_structuur_detectie.md`.
- M2: module 2 (calculator via EcoLogits) met tests, zie
  `specs/spec_carbon_calculator.md`.
- M3: deze pijplijn, aggregatie en rapportage met end-to-end tests op een
  synthetische export.

## Definition of Done

- elke vereiste (FR en NFR) van de milestones heeft tests die slagen.
- `harness/run_tests.sh` geeft exit code 0; mypy en ruff geven geen fouten.
- de aanroepvorm van EcoLogits (bibliotheek of lokale API), de default-zones en
  de configtabel met datacenterregio's staan in `docs/ADR/`.
- de demo draait op de echte voorbeelden in `context/example_data_dump/`
  (mistral) en op een openai-`conversations.json`.
- verbetersuggesties tijdens het werk staan in `improvements.md`.

