# ADR: carbon calculator via de EcoLogits-bibliotheek

Datum: 2026-10-28

Status: geaccepteerd

## Context

De carbon calculator (spec `specs/spec_carbon_calculator.md`, mileston M2a en
M2b) schat per assistant-bericht de energie (kWh) en uitstoot (kg CO2eq) van
een modelantwoord. De spec laat de keuze tussen twee aanroepvormen:

1. de EcoLogits-API, `POST /v1/estimations` met de velden `provider`, `model`,
   `output_token_count` en optioneel `electricity_mix_zone`. De API is open
   source en draait lokaal in een container (project `mlco2/ecologits-api`).
2. de Python-bibliotheek `ecologits` (`pip install ecologits`).

Eisen uit de spec die de keuze bepalen:

- NFR-1 offline: geen extern netwerkverkeer, alle gegevens in de package.
- NFR-3: `ecologits` is de enige runtime-dependency; tiktoken alleen test-only.
- FR-3: alle energie- en emissiecijfers komen uit EcoLogits; de module mag geen
  eigen rekenmodel hebben.

## Beslissing

We gebruiken de Python-bibliotheek `ecologits` en roepen de functie
`llm_impacts` uit `ecologits.tracers.utils` aan met de parameters `provider`,
`model_name`, `output_token_count`, `request_latency` en
`electricity_mix_zone`.

Motive:

- `llm_impacts` is dezelfde high-level functie die de officiële EcoLogits-API
  intern gebruikt voor `/v1/estimations`. De FR-3-integratietest vergelijkt
  daarom direct met deze functie.
- De bibliotheek is MPL-2.0, zoals de spec vermeldt. De API-server is AGPL-3.0
  en heeft fastapi, uvicorn en een proxy-proces nodig, dat zijn extra
  runtime-dependencies die NFR-3 niet toestaat.
- Geen los proces of container nodig; daardoor schaalt de bulkberekening
  (NFR-2, 100.000 berichten binnen 5 minuten) zonder procesbeheer.

De providernaam `mistral` wordt in de koppeling vertaald naar `mistralai`,
de naam die EcoLogits in zijn modelgegevens gebruikt. `openai` blijft
`openai`.

## Gevolgen

- `ecologits>=0.10.2,<1.0.0` is de enige runtime-dependency in `pyproject.toml`.
- `ecologits.tracers.utils.llm_impacts` is niet het klassieke publieke
  `EcoLogits.init`-pad (dat instrumenteert live OpenAI-clients). De koppeling
  is geïsoleerd in `src/carbon_calculator/ecologits_koppeling.py`, zodat een
  wijziging in de upstream-API op één plek landt.
- De versie van de modelgegevens (aanname A2) wordt per berekening meegeleverd
  via `ecologits.__version__`.
- Het resultaat wordt per bericht bewaard met energie en uitstoot als bereik
  (laag, hoog, gemiddelde), de gebruikte zones en de versie (FR-4).

## Default-zones en bandbreedte (FR-5, FR-6)

De primaire zone per provider is configureerbaar en default `WOR`. Om de
onzekerheid van de energiemix zichtbaar te houden (FR-6) rekent de calculator
altijd met minstens twee unieke zones:

1. de geconfigureerde zone per provider, anders `WOR`;
2. de datacenterregio uit de configtabel (zie hieronder), anders `WOR`;
3. als 1 en 2 samenvallen: `EEE` als alternatief.

De laag-hoog range in het resultaat is het minimum en maximum van de
zone-gemiddelden die EcoLogits zelf teruggeeft. De individuele min-max
onzekerheid per zone blijft beschikbaar in `uitkomsten_per_zone`.

Een zone die EcoLogits niet kent geeft een `OngeldigeZoneError` met de zone en
geldige voorbeelden (FR-5). Geldig zijn de ISO 3166-1 alpha-3 codes plus `WOR`
en `EEE` (aanname A1).

## Configtabel met datacenterregio's (A3)

Aanname uit de spec: de tabel met bekende datacenterregio's staat als data los
van de code. De tabel staat in `src/carbon_calculator/data/datacenter_regios.json`
en is een schatting uit disclosures, geen garantie:

| provider | zone | toelichting |
|---|---|---|
| openai | USA | ChatGPT draaide historisch via Azure-datacenters in de VS |
| mistral | EEE | Mistral draait op Europese datacenters; EEE is het Europese gemiddelde |

Deze tabel kan onder begeleiding van een nieuwe ADR worden bijgewerkt zonder
code te wijzigen (de berekening laadt alleen de zone uit de table).

## Tokenschatting en markering (FR-1, FR-8)

De v1-vuistregel is 1 token per 4 tekens (`len(inhoud) // 4`), volledig
deterministisch en alleen de standaardbibliotheek. De acceptatietest
vergelijkt op een referentieset van 60 westerse teksten (statische fixture in
`tests/fixtures/carbon_calculator/referentieset.json`) met de
tiktoken-telling (cl100k_base); elke tekst blijft binnen 25% afwijking.
tiktoken zit alleen in de dev-extra's.

Een bericht wordt als niet-westers gemarkeerd (FR-8) wanneer het minstens 5
tekens buiten de Latijnse blokken bevat en het aandeel daarvan minstens 10%
is. Whitespace, cijfers, interpunctie en wiskundige symbolen tellen daarbij
niet mee.

## Request-latency (A4)

EcoLogits kan een request-latency in seconden vragen. Bij bulkberekeningen
zonder gemeten latency gebruikt de koppeling de vaste default `inf` en meldt
dat per bericht via `latency_aangenomen` en globaal in het rapport.

## Provider-defaults en fallback (FR-7)

De berekening accepteert per provider een standaardmodel en een globaal
fallback-model. Daarnaast voorziet de config in een standaard basismodel per
provider (`STANDAARD_PROVIDER_MODELLEN` in `src/carbon_calculator/config.py`).
Voor mistral geldt dat basismodel standaard, want een mistral-export bevat
nooit modelinformatie; zonder die default zou elk mistral-bericht worden
overgeslagen. De volgorde voor een bericht met attributie `onbekend` is:
provider-standaardmodel, dan globaal fallback-model, dan het standaard
basismodel. Expliciete configuratie wint altijd. Alleen als geen van de drie
een model oplevert dat EcoLogits voor de provider kent, wordt het bericht
overgeslagen en telt het niet mee in de som, met de reden in het resultaat.
