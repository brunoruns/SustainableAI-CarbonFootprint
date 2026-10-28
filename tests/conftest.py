"""Gedeelde fixtures en paden voor de structuurdetectie-, calculator- en bulk-tests."""

import json
from pathlib import Path

import pytest

from carbon_calculator import BerekenConfig
from structuur_detectie import Bericht, Gesprek

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def openai_export() -> Path:
    """Pad naar de synthetische openai conversations.json."""
    return _FIXTURES / "openai" / "conversations.json"


@pytest.fixture()
def mistral_export() -> Path:
    """Pad naar de synthetische mistral chat-export map."""
    return _FIXTURES / "mistral" / "chat-export-1700000000000"


@pytest.fixture()
def onbekend_export() -> Path:
    """Pad naar een export zonder gekend formaat."""
    return _FIXTURES / "onbekend"


@pytest.fixture()
def misleidend_export() -> Path:
    """Pad naar een export die op mistral lijkt, maar niet parseert."""
    return _FIXTURES / "misleidend" / "chat-export-999"


@pytest.fixture()
def echte_mistral_export() -> Path:
    """Pad naar de echte mistral-voorbeelden uit context/example_data_dump."""
    mistral = _FIXTURES.parents[1] / "context" / "example_data_dump" / "mistral"
    exports = sorted(mistral.glob("chat-export-*")) if mistral.is_dir() else []
    if not exports:
        pytest.skip("echte mistral-export ontbreekt in context/example_data_dump/")
    return exports[0]


@pytest.fixture()
def referentieset() -> list[str]:
    """De westerse referentieset voor de tokenschattingsacceptatie (FR-1)."""
    pad = _FIXTURES / "carbon_calculator" / "referentieset.json"
    data = json.loads(pad.read_text(encoding="utf-8"))
    return [str(tekst) for tekst in data]


@pytest.fixture()
def calculator_gesprek() -> Gesprek:
    """Een canoniek gesprek met een openai-assistant-bericht voor calculator-tests."""
    berichten = [
        Bericht(
            id="m1",
            rol="user",
            inhoud="Wat is de opbrengst van zonnepanelen in de winter?",
            created_at=1733294335.0,
            model=None,
        ),
        Bericht(
            id="m2",
            rol="assistant",
            inhoud="The output of solar panels depends on the location and the season.",
            created_at=1733294339.5,
            model="gpt-4o-mini",
        ),
    ]
    return Gesprek(
        id="conv-1",
        titel="Voorbeeld",
        provider="openai",
        created_at=1733294335.0,
        berichten=berichten,
    )


@pytest.fixture()
def gemengde_gesprekken() -> list[Gesprek]:
    """Een synthetische, 'gemengde' export: één openai- en één mistral-gesprek.

    De berichten liggen over twee maanden (januari en februari 2024, UTC) zodat
    de per-maand-aggregatie getest kan worden. De openai-berichten gebruiken
    epoch-seconden, de mistral-berichten ISO 8601 met Z-suffix.
    """
    openai = Gesprek(
        id="conv-openai",
        titel="OpenAI voorbeeld",
        provider="openai",
        created_at=1704067200.0,
        berichten=[
            Bericht(
                id="o1",
                rol="user",
                inhoud="Wat is de opbrengst van zonnepanelen in de winter?",
                created_at=1704067200.0,
                model=None,
            ),
            Bericht(
                id="o2",
                rol="assistant",
                inhoud="The solar yield depends on location, season and panel orientation.",
                created_at=1704067210.0,
                model="gpt-4o-mini",
            ),
        ],
    )
    mistral = Gesprek(
        id="conv-mistral",
        titel=None,
        provider="mistral",
        created_at="2024-02-01T00:00:01.000Z",
        berichten=[
            Bericht(
                id="m1",
                rol="user",
                inhoud="Waar draaien jullie servers?",
                created_at="2024-02-01T00:00:01.000Z",
                model=None,
            ),
            Bericht(
                id="m2",
                rol="assistant",
                inhoud="Our servers run in European datacenters to keep data local.",
                created_at="2024-02-01T00:00:02.000Z",
                model=None,
            ),
        ],
    )
    return [openai, mistral]


@pytest.fixture()
def gemengde_config() -> BerekenConfig:
    """Config voor de gemengde export: mistral rekenmodellen via provider-default."""
    return BerekenConfig(provider_standaard_modellen={"mistral": "mistral-large-2512"})

