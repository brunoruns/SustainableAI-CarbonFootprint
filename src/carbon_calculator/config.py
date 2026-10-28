"""Configuratie voor de carbon calculator.

De config bepaalt per provider de primaire elektriciteitsmix-zone (default
`WOR`, zie FR-5 en A1) en de opties waarmee `onbekend` modellen alsnog mogen
meetellen (FR-7). Zie `STANDAARD_PROVIDER_MODELLEN` voor het standaard
basismodel per provider.

A3 uit de spec: de configtabel met de datacenterregio's per aanbieder staat
als data los van de code (zie `data/datacenter_regios.json`), niet in deze
config.
"""

from dataclasses import dataclass, field

STANDAARD_PROVIDER_MODELLEN: dict[str, str] = {
    "mistral": "mistral-large-2512",
}
"""Standaard-basismodel per provider voor berichten met attributie `onbekend`.

Voor mistral geldt dit standaard, want een mistral-export bevat nooit
modelinformatie en de attributie is daardoor altijd `onbekend` (FR-2, zie de
spec). Zonder dit basismodel zou elk mistral-bericht worden overgeslagen
(FR-7). De gebruiker kan het basismodel altijd overschrijven met een
provider-standaardmodel of het globale fallback-model in `BerekenConfig`;
expliciete configuratie wint van deze default. EcoLogits moet het model kennen
voor de provider, anders wordt het bericht alsnog overgeslagen.
"""


@dataclass(frozen=True)
class BerekenConfig:
    """Instelbare opties voor de berekening.

    Attributes:
        zones_per_provider: primaire elektriciteitsmix-zone per provider.
            De default is `WOR` (zie FR-5). De zone moet door EcoLogits
            ondersteund worden, anders geeft de berekening een duidelijke fout.
        provider_standaard_modellen: standaardmodel per provider voor berichten
            zonder modelinformatie (bijvoorbeeld mistral). Wint van het globale
            fallback-model en van `STANDAARD_PROVIDER_MODELLEN`.
        gesprek_standaard_modellen: een eventueel `default_model_slug` per
            gesprek-id uit de openai-export.
        fallback_model: fallbackmodel voor elk bericht waarvan de attributie
            `onbekend` is, als er geen provider-standaardmodel bestaat. Wint
            van het standaard basismodel uit `STANDAARD_PROVIDER_MODELLEN`.
        request_latency: gemeten request-latency in seconden (A4). `None`
            betekent: geen latency gemeten, de vaste default van EcoLogits
            wordt gebruikt en dat wordt gemeld.
    """

    zones_per_provider: dict[str, str] = field(default_factory=dict)
    provider_standaard_modellen: dict[str, str] = field(default_factory=dict)
    gesprek_standaard_modellen: dict[str, str] = field(default_factory=dict)
    fallback_model: str | None = None
    request_latency: float | None = None
