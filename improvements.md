# Verbetersuggesties

Opgedaan tijdens het testen van `specs/spec_structuur_detectie.md` (M1a + M1b).

- [ ] `detecteer()` en `parseer()` voeren nu beide de volledige parse uit.
      Voor een CLI die alleen de provider toont volstaat een snelle
      kenmerkcheck zonder te parsen.
- [ ] Zip-ondersteuning en exports met meerdere aanbieders (open punt 2)
      horen thuis in de pijplijn, niet in module 1.
- [ ] Een handmatige override (open punt 3) is al mogelijk via de registry
      (FR-7), maar een expliciete gebruikerskeuze is nog niet ingebouwd.
- [ ] De kenmerkscore wordt per parser per aanroep herberekend. Nu ruim
      binnen NFR-2, maar een kleine scorecache in de Registry houdt
      detectie ook bij grotere exports voorspelbaar snel.
- [ ] De echte mistral-data bevat één leeg `chat-*.json`-bestand. Bewuste
      keuze: een leeg bestand levert een gesprek zonder berichten en geen
      fout.
- [ ] De voorbeelddata in `context/` bevat Python-bestanden uit gesprekken.
      mypy en ruff sluiten `context/` daarom uit via `pyproject.toml`.
- [ ] `.clinerules` vraagt om code in een container te draaien, maar er is geen
      devcontainer-configuratie in de repo. Een `.devcontainer/` met de
      dev-tooling (ruff, mypy, pytest) maakt de workflow reproduceerbaar.
- [ ] De README-documentatie is toegevoegd; de voorbeelden zijn handmatig
      geverifieerd tegen de fixtures in `tests/fixtures/`.

Opgedaan tijdens het testen van `specs/spec_carbon_calculator.md` (M2a + M2b).

- [ ] De vuistregel (1 token per 4 tekens) overschat systematisch formele
      Engelse tekst met lange woorden (tiktoken-ratio tot 6 tekens per token).
      De referentieset voldoet, maar een v2-vuistregel (bijvoorbeeld 1 token
      per 4,5 tekens) of een betere schatting verdient een eigen spec.
- [ ] de koppeling gebruikt `ecologits.tracers.utils.llm_impacts`, de interne
      functie van de officiële API. De functie is geïsoleerd in
      `ecologits_koppeling.py`, maar bij upgrades van ecologits (>=0.10.2)
      moet die plek even gecheckt worden.
- [ ] Het canonieke model bevat geen `default_model_slug` van een
      openai-gesprek; de calculator krijgt dat via `gesprek_standaard_modellen`
      in de config. De bulk-pijplijn (M3) moet die waarde uit de ruwe export
      leveren, en het is een optie om het veld later aan het canonieke model
      toe te voegen.
- [ ] De NFR-2-test meet 5.000 berichten binnen 1 minuut; de eis is 100.000
      binnen 5 minuten. Een benchmark van 100.000 berichten kan bij releases
      als regressiegate dienen; in reguliere runs is die te zwaar.
- [ ] Ongeldige providers geven nu een duidelijke fout; een registry voor
      provider-koppelingen (vergelijkbaar met module 1) maakt het
      toevoegen van nieuwe aanbieders later eenvoudiger.
- [ ] Het rapport rapporteert de versie van de modelgegevens als
      `ecologits.__version__`; een expliciete data-revisie (bijvoorbeeld
      de hosted models.json datum) maakt A2 nog preciezer.

Opgedaan tijdens het schrijven van de tests voor
`specs/spec_bulk_analyser.md` (M3, pijplijn nu geïmplementeerd).

- [x] De bulk-pijplijn (M3) is geïmplementeerd in `src/bulk_analyser/`
      (pijplijn, aggregatie, rapport). Het publieke contract uit
      `tests/test_bulk_analyser_*.py` en de hele harness slagen (exit 0).
- [ ] EcoLogits kent mistral-modellen alleen onder de providernaam `mistralai`
      (de koppeling `_ecologits_provider` vertaalt dat). In de tests en de
      demo-config betekent dat: een mistral-model komt alleen als
      provider-default of fallback mee, nooit via `model` in de export.
- [ ] De aggregatie groepeert per model op `attributie` (dus ook `onbekend`),
      niet op het rekenmodel, zodat het aandeel onbekende modellen zichtbaar
      blijft als er een fallback is ingesteld.
- [ ] FR-6 'elk aggregaat vermeldt de provider' is pragmatisch ingevuld: het
      gespreks- en provideraggregaat dragen de provider. Een per-maand-aggregaat
      is bewust alleen gesleuteld op de maand, niet op provider; wil de spec
      dat wel, dan worden `per_maand`-sleutels `("provider", "YYYY-MM")`.
- [ ] Berichten zonder `created_at` kunnen niet in een maandgroep vallen; de
      som over `per_maand` is dan kleiner dan het totaal. De fixtures uit de
      tests geven elk assistant-bericht een tijdstip zodat de controlesom
      (FR-2) exact blijft.
- [ ] Er is nog geen `.devcontainer/`; .clinerules vraagt om code in een
      container te draaien. De tests draaien nu in de WSL-venv met Python
      3.13, waar ecologits 0.11.3 geïnstalleerd is.
- [ ] De zip-verwerking pakt in een tijdelijke map; voor hele grote exports
      kan streaming uit een zip (zonder helemaal uit te pakken) een volgende
      optimalisatie zijn. Nu blijft de NFR-2-test ruim binnen de eis.
- [ ] `structuur_detectie` kreeg een nieuwe helper `analyseer_bron` die
      provider, formatnaam en gesprekken in één gang levert, zodat de pijplijn
      geen dubbele detectie draait. De module-1-API is verder onveranderd.

Opgedaan tijdens het implementeren van `specs/spec_cli.md` (M4, CLI
`co2chat` nu geïmplementeerd).

- [x] De CLI staat in `src/cli/main.py` (argparse, config-mapper, uitvoer en
      foutafhandeling) en is geregistreerd als console-script
      `co2chat = "cli.main:main"` in `pyproject.toml`. De hele harness
      (ruff, mypy, pytest) slaagt, ook op de echte mistral-voorbeelden.
- [ ] `bulk_analyser` kreeg een nieuwe publieke helper `vind_aanbieders` die
      de aanbieders van een export (map, bestand of zip) detecteert, zodat de
      CLI `--zone` en `--model` per aanbieder in de config kan zetten zonder
      eigen detectielogica (FR-4, A3).
- [ ] Met `--zone` of `--model` parseert de CLI de export twee keer: een keer
      in `vind_aanbieders` (voor de config) en een keer in `analyseer`. Nu
      ruim binnen NFR-2, maar een analyseer-variant die de config tijdens de
      detectie opbouwt bespaart bij grote exports een volledige parse.
- [ ] De zip-afhandeling in `_vind_aanbieders_in_zip` spiegelt de
      try/except uit `_analyseer_zip`. Een gedeelde contextmanager
      (`_als_bron_in_gebruik`) haalt die duplicatie weg zodra er weer in de
      pijplijn gewerkt wordt.
- [ ] EcoLogits schrijft waarschuwingen (bijvoorbeeld 'model architecture has
      not been released') naar stderr tijdens de analyse. Ze zijn
      informatiever dan foutief, maar een optie om ze te filteren of naar een
      logbestand te sturen houdt stderr vrij voor de eigen foutmeldingen.
- [ ] De CLI schrijft de output byte-identiek aan `genereeer_json` en
      `genereeer_markdown` (dus zonder extra afsluitende newline). De
      NFR-5-acceptatie is daardoor een exacte stringvergelijking in de tests.

## Standaard basismodel voor mistral (FR-7)

- [x] Mistral-berichten krijgen standaard een basismodel via
      `STANDAARD_PROVIDER_MODELLEN` in `src/carbon_calculator/config.py`
      (`mistral-large-2512`), zodat mistral-exports zonder extra config worden
      berekend in plaats van overgeslagen. De volgorde blijft: expliciet
      provider-standaardmodel, expliciet fallback-model, dan het basismodel.
      Spec, ADR en README zijn bijgewerkt.



