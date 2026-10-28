# Spec: carbon calculator voor chat exports

## Doel

Deze module berekent per assistant-bericht de geschatte energie (kWh) en
uitstoot (kg CO2eq) van een modelantwoord, met EcoLogits als rekenkern.
Energie- en emissiecijfers nemen we over van bestaande tools en datasets, we
bouwen geen eigen rekenmodel.

Deze spec hoort bij de bulk analyser uit `specs/spec_bulk_analyser.md` en
draait op het canonieke model uit `specs/spec_structuur_detectie.md`.

## Waarom EcoLogits en niet codecarbon

codecarbon meet emissies van code die lokaal op de eigen hardware draait. Een
chat export is een reeks API-calls uit het verleden, daar is geen lokale
uitvoering om te meten. De makers van codecarbon verwijzen voor remote GenAI
API-calls (OpenAI, Anthropic, Mistral enzovoort) expliciet naar EcoLogits, hun
eigen zusterproject binnen de CodeCarbon non-profit.

EcoLogits schat per request de impact op basis van provider, model,
tokenhoeveelheid en elektriciteitsmix-zone. codecarbon blijft gereserveerd
voor de latere live-metingsmodule van de app.

## Rekenstap per bericht

Voor elk assistant-bericht:

1. schat het aantal tokens van de inhoud (zie 'Tokenschatting').
2. bepaal het model (zie 'Modelattributie').
3. roep EcoLogits aan met provider, model, tokens en een elektriciteitsmix-zone.
4. bewaar het resultaat bij het bericht: energie in kWh en uitstoot in kg
   CO2eq, elk als bereik (laag, hoog, gemiddelde), plus de gebruikte zone en
   de versie van de modelgegevens.

Aanroepvorm, te kiezen bij implementatie:
- via de EcoLogits API: `POST /v1/estimations` met velden `provider`, `model`,
  `output_token_count` en optioneel `electricity_mix_zone`. Deze API is open
  source en draait ook lokaal in een container.
- of via de Python-bibliotheek `ecologits` (pip install ecologits).

De keuze wordt vastgelegd in `docs/ADR/` (zie Milestones). Uitgangspunt is:
de berekening kan volledig offline en lokaal draaien, er wordt geen live
API-call naar een model gedaan.

## Tokenschatting

De exports bevatten geen tokenaantallen, daarom schatten wij het aantal tokens
uit de tekst:

- vuistregel in v1: 1 token per 4 tekens (ASCII en westerse tekst).
- de schatting is deterministisch: zelfde input, zelfde uitkomst.
- referentietest: op een referentieset met westerse teksten wijkt de schatting
  maximaal 25% af van de tiktoken-telling. tiktoken is dan test-only, de
  vuistregel zelf gebruikt alleen de standaardbibliotheek.
- teksten met veel niet-westerse tekens worden in het rapport gemarkeerd,
  want de vuistregel onderschat die sterk (FR-8).

## Modelattributie

- openai: `model_slug` uit de metadata van het assistant-bericht, anders
  `default_model_slug` van het gesprek, anders `onbekend`.
- mistral: de export bevat geen modelinformatie, attributie is altijd
  `onbekend`. Voor mistral voorziet de config standaard in een basismodel
  (`STANDAARD_PROVIDER_MODELLEN`), zodat mistral-berichten standaard meetellen.
- `onbekend` modellen geven een waarschuwing en tellen mee via de
  provider-default, het fallback-model of het standaard basismodel uit de
  config (FR-7). Zonder een van de drie wordt het bericht overgeslagen.

## Locatie van uitvoering en energiemix

Waar de code draaide bepaalt grotendeels de uitstoot: dezelfde request stoot
in een kolenland tot tien keer meer CO2 uit dan op groene stroom. De
serverlocatie is per request echter onbekend en aanbieders publiceren die niet
per request. EcoLogits rekent met een elektriciteitsmix-zone per
ISO 3166-1 alpha-3 code, met `WOR` (wereldgemiddelde) als default en
bijvoorbeeld `EEE` (Europees gemiddelde) als optie.

Manieren om de waarschijnlijke zone te bepalen, in volgorde van voorkeur:

1. de gebruiker kiest de zone per provider via config. Dit is de primaire bron
   en maakt de onzekerheid bespreekbaar.
2. een configtabel met de bekende datacenterregio per aanbieder, opgebouwd uit
   disclosures van de aanbieders en vastgelegd in een ADR. Voorbeelden voor de
   demo: openai (ChatGPT) draaide historisch via Azure in de VS, mistral in de
   EU. Dit is een schatting, geen garantie, en kan per periode veranderen.
3. indirect bewijs uit live verkeer (bijvoorbeeld de cf-ray-header van
   Cloudflare onthult een kololocatie, of latencymeting aan provider-endpoints)
   is alleen beschikbaar bij live gebruik, niet achteraf voor een bulk export.
   Deze bron hoort thuis in de latere live-module.
4. fallback: `WOR`, de default van EcoLogits. Het rapport vermeldt dit altijd
   expliciet.

Bandbreedte: de calculator voert de berekening uit voor minstens twee
plausibele zones en het rapport toont de laag-hoog range, zodat de impact van
deze keuze zichtbaar blijft (FR-6).

## Databronnen

- EcoLogits (MPL-2.0, van de CodeCarbon non-profit): model-intensiteiten en
  emissiefactoren als open data in de package.
- CLEER-data (CC BY-NC 4.0): optionele referentie. Niet commercieel inzetbaar
  zonder toestemming van Sustainable AI Group.
- AIEnergyScore: optionele referentie per taak (bijvoorbeeld tekstgeneratie).
- geen zelfgebouwde intensiteitentabel in v1 (zie open punt 1).

## Functionele vereisten

- FR-1 tokenschatting: de schatting is deterministisch en wijkt op de
  referentieset maximaal 25% af van de tiktoken-telling. Acceptatie: de test
  uit 'Tokenschatting' slaagt voor minstens 50 voorbeeldteksten.
- FR-2 modelattributie: elk bericht heeft precies één modelwaarde via de
  volgorde uit 'Modelattributie'. Acceptatie: het aantal `onbekend`-berichten
  staat in de output van de module.
- FR-3 EcoLogits-integratie: alle energie- en emissiecijfers komen uit
  EcoLogits, de module bevat geen eigen energie- of uitstootlogica. Acceptatie:
  de integratietest geeft dezelfde waarden als EcoLogits zelf bij dezelfde
  parameters.
- FR-4 uitkomst per bericht: energie (kWh) en uitstoot (kg CO2eq) als bereik,
  met zone en versie van de modelgegevens. Acceptatie: alle velden aanwezig en
  reproduceerbaar bij dezelfde configuratie.
- FR-5 zone instelbaar: de zone is per provider configureerbaar, met `WOR` als
  default. Acceptatie: een ongeldige zone geeft een duidelijke fout.
- FR-6 bandbreedte: de berekening draait voor minstens twee zones en levert
  een laag-hoog range. Acceptatie: de range bevat beide uitkomsten.
- FR-7 onbekend model: `onbekend` modellen leveren een waarschuwing en tellen
  via de provider-default, het fallback-model of het standaard basismodel uit
  `STANDAARD_PROVIDER_MODELLEN`. Voor mistral geldt dat basismodel standaard,
  want een mistral-export bevat nooit modelinformatie. Acceptatie: zonder een
  van de drie wordt het bericht overgeslagen, wijkt de totaalsom niet uit en
  staat het aantal overgeslagen berichten in het resultaat.
- FR-8 niet-westerse tekst: berichten waarbij de vuistregel sterk kan
  onderschatten worden gemarkeerd. Acceptatie: de markering staat per bericht
  in de uitvoer van de module.

## Niet-functionele vereisten

- NFR-1 offline: de berekening vereist geen extern netwerkverkeer; de gebruikte
  gegevens zitten in de package of in lokale config en de lokale EcoLogits-API.
- NFR-2 prestaties: 100.000 berichten worden binnen 5 minuten berekend op
  reguliere hardware.
- NFR-3 afhankelijkheden: `ecologits` is de enige runtime-dependency;
  `tiktoken` mag alleen in tests gebruikt worden.
- NFR-4 kwaliteit: Python 3.12+, type hints, Google-style docstrings, pytest,
  geen ongebruikte imports of variabelen.

## Randvoorwaarden en aannames

- A1 de EcoLogits-zones beperken zich tot ISO 3166-1 alpha-3 plus `WOR` en
  `EEE`, zoals de library die ondersteunt.
- A2 modelintensiteiten veranderen in de tijd; het resultaat vermeldt altijd
  de gebruikte versie van de modelgegevens.
- A3 de configtabel met datacenterregio's per aanbieder staat als data los van
  de code en wordt bijgewerkt onder begeleiding van een ADR.
- A4 EcoLogits kan een request-latency als invoer vragen; bij bulkberekeningen
  zonder latency gebruiken we een vaste default en melden we dat in de range.

## Open punten (voor overleg)

1. vergelijken we uitkomsten met CLEER of AIEnergyScore als extra controlebron
   in v1, of pas later.
2. welke providers en regio's komen in de demo-configtabel (voorstel: openai
   via Azure in de VS, mistral in de EU).
3. wil de gebruiker de zone per provider kiezen in de eerste demo, of volstaat
   `WOR` plus bandbreedte als eerste versie.

## Milestones en Definition of Done

Milestone M2a: tokenschatting en modelattributie met tests (FR-1, FR-2, FR-8).

Milestone M2b: EcoLogits-integratie (bibliotheek of lokale API), zone-logica en
bandbreedte met tests (FR-3 tot en met FR-7).

Definition of Done:
- alle FRs en NFRs hebben tests die slagen.
- `harness/run_tests.sh` geeft exit code 0, mypy en ruff geven geen fouten.
- `docs/ADR/` bevat de keuze voor de aanroepvorm (API of bibliotheek), de
  default-zones en de configtabel met datacenterregio's.
- de berekening is reproduceerbaar:zelfde versie en config geeft zelfde cijfers.
- verbetersuggesties tijdens het werk staan in `improvements.md`.

