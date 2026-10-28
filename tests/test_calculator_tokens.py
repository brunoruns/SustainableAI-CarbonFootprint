"""Tests voor de tokenschatting (FR-1) en de niet-westerse markering (FR-8)."""

import pytest
import tiktoken

from carbon_calculator import is_niet_westers, schat_tokens

_ENCODING = "cl100k_base"


def test_fr1_schatting_is_deterministisch() -> None:
    tekst = "Dit is een gewone westerse tekst met een beknopt antwoord."
    assert schat_tokens(tekst) == schat_tokens(tekst) == schat_tokens(tekst)
    assert schat_tokens(tekst) == len(tekst) // 4


def test_fr1_lege_en_korte_teksten() -> None:
    assert schat_tokens("") == 0
    assert schat_tokens("hallo!") == 1
    assert schat_tokens("abcdefgh") == 2


def test_fr1_referentieset_wijkt_maximaal_25_procent_af(
    referentieset: list[str],
) -> None:
    """Acceptatie FR-1: minstens 50 westerse teksten, alle binnen 25% van tiktoken."""
    assert len(referentieset) >= 50
    try:
        codering = tiktoken.get_encoding(_ENCODING)
    except Exception as fout:  # pragma: no cover - alleen als de vocab niet te laden is
        pytest.skip(f"tiktoken-vocab niet beschikbaar: {fout}")
    for tekst in referentieset:
        telling = len(codering.encode(tekst))
        assert telling > 0
        afwijking = abs(schat_tokens(tekst) - telling) / telling
        assert afwijking <= 0.25, (
            f"tekst wijkt {afwijking:.1%} af van tiktoken: {tekst[:60]!r}"
        )


def test_fr8_westerse_tekst_wordt_niet_gemarkeerd() -> None:
    assert not is_niet_westers("The weather is nice today, so we can go for a walk.")
    tekst_met_accenten = "Hé, dit is een mooi verhaal met een héél café en een crème brûlée."
    assert not is_niet_westers(tekst_met_accenten)


def test_fr8_tekst_met_veel_cjk_wordt_gemarkeerd() -> None:
    tekst = "你好，世界！今天的天气非常好，所以我们决定去公园散步。"
    assert is_niet_westers(tekst)


def test_fr8_tekst_met_verspreide_cyrillische_letters_wordt_gemarkeerd() -> None:
    tekst = "Привет, как дела? Всё хорошо, спасибо большое за вашу помощь."
    assert is_niet_westers(tekst)
