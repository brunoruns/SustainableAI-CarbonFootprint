"""Parsers voor de ondersteunde exportformaten: openai en mistral."""

import json
from pathlib import Path
from typing import Any

from structuur_detectie.canoniek import Bericht, Gesprek
from structuur_detectie.fouten import ParseFout

_ROLLEN = frozenset({"user", "assistant", "system", "tool"})


def _laad_json(pad: Path) -> Any:
    """Laad een JSON-bestand, of geef een ParseFout."""
    try:
        with pad.open(encoding="utf-8") as bestand:
            return json.load(bestand)
    except (OSError, json.JSONDecodeError) as fout:
        raise ParseFout(f"ongeldige JSON in '{pad}': {fout}") from fout


def _tekst(waarde: object) -> str:
    """Geef de waarde als tekst terug, anders een lege string."""
    return waarde if isinstance(waarde, str) else ""


def _opt_tekst(waarde: object) -> str | None:
    """Geef de waarde als tekst terug, anders None."""
    return waarde if isinstance(waarde, str) else None


def _tijdstip(waarde: object) -> float | str | None:
    """Zet een tijdstip om naar epoch-seconden of ISO-tekst."""
    if isinstance(waarde, bool):
        return None
    if isinstance(waarde, (int, float)):
        return float(waarde)
    return waarde if isinstance(waarde, str) else None


def _inhoud_uit_content(content: object) -> str:
    """Voeg de tekstuele delen van een content-object samen tot één tekst."""
    if not isinstance(content, dict):
        return ""
    delen: list[str] = []
    parts = content.get("parts")
    if isinstance(parts, list):
        for deel in parts:
            if isinstance(deel, str):
                delen.append(deel)
            elif isinstance(deel, dict):
                delen.append(_tekst(deel.get("text")))
    if not delen:
        for sleutel in ("text", "result"):
            waarde = content.get(sleutel)
            if isinstance(waarde, str):
                delen.append(waarde)
    return "".join(delen)


def _sorteer_sleutel(bericht: Bericht) -> tuple[int, float | str]:
    """Sorteersleutel: onbekende tijden blijven stabiel als laatste (FR-6)."""
    if bericht.created_at is None:
        return (1, "")
    return (0, bericht.created_at)


def _sorteer_berichten(berichten: list[Bericht]) -> list[Bericht]:
    """Sorteer berichten chronologisch op created_at, stabiel bij null."""
    return sorted(berichten, key=_sorteer_sleutel)


def _bericht_uit_openai_knoop(knoop: dict[str, Any]) -> Bericht | None:
    """Maak een canoniek bericht uit een openai-mapping-knoop."""
    boodschap = knoop.get("message")
    if not isinstance(boodschap, dict):
        return None
    auteur = boodschap.get("author")
    rol = auteur.get("role") if isinstance(auteur, dict) else None
    if not isinstance(rol, str) or rol not in _ROLLEN:
        raise ParseFout(f"onbekende rol in openai-export: {rol!r}")
    metadata = boodschap.get("metadata")
    model = metadata.get("model_slug") if isinstance(metadata, dict) else None
    return Bericht(
        id=_opt_tekst(boodschap.get("id")),
        rol=rol,
        inhoud=_inhoud_uit_content(boodschap.get("content")),
        created_at=_tijdstip(boodschap.get("create_time")),
        model=_opt_tekst(model),
    )


def _actief_pad_berichten(gesprek: dict[str, Any]) -> list[Bericht]:
    """Bepaal de berichten op het pad van de wortel tot current_node (FR-4)."""
    mapping = gesprek.get("mapping")
    if not isinstance(mapping, dict):
        raise ParseFout("openai-gesprek mist een 'mapping'")
    huidige: object = gesprek.get("current_node")
    knopen: list[dict[str, Any]] = []
    gezien: set[str] = set()
    while isinstance(huidige, str) and huidige in mapping and huidige not in gezien:
        knoop = mapping[huidige]
        if not isinstance(knoop, dict):
            break
        knopen.append(knoop)
        gezien.add(huidige)
        huidige = knoop.get("parent")
    berichten: list[Bericht] = []
    for knoop in reversed(knopen):
        bericht = _bericht_uit_openai_knoop(knoop)
        if bericht is not None:
            berichten.append(bericht)
    return _sorteer_berichten(berichten)


def _parse_openai_gesprek(gesprek: dict[str, Any]) -> Gesprek:
    """Parse één openai-gesprek naar een canoniek gesprek."""
    id_ = gesprek.get("id")
    if not isinstance(id_, str):
        raise ParseFout("openai-gesprek mist een 'id'")
    return Gesprek(
        id=id_,
        titel=_opt_tekst(gesprek.get("title")),
        provider="openai",
        created_at=_tijdstip(gesprek.get("create_time")),
        berichten=_actief_pad_berichten(gesprek),
    )


def parse_openai_export(bron: Path) -> list[Gesprek]:
    """Parse een openai conversations.json naar het canonieke model."""
    data = _laad_json(bron)
    if not isinstance(data, list):
        raise ParseFout("openai-export moet een lijst van gesprekken zijn")
    gesprekken: list[Gesprek] = []
    for item in data:
        if not isinstance(item, dict):
            raise ParseFout("openai-export bevat een gesprek dat geen object is")
        gesprekken.append(_parse_openai_gesprek(item))
    return gesprekken


def score_openai(bron: Path) -> float:
    """Geef een kenmerkscore voor het openai-formaat."""
    if not (bron.is_file() and bron.name == "conversations.json"):
        return 0.0
    score = 10.0
    try:
        data = _laad_json(bron)
    except ParseFout:
        return score
    if not (isinstance(data, list) and data and isinstance(data[0], dict)):
        return score
    if "mapping" in data[0] and "current_node" in data[0]:
        score += 5.0
    return score


def _vind_chat_bestanden(bron: Path) -> list[Path]:
    """Geef de chat-*.json bestanden van een export (map of los bestand)."""
    if bron.is_file():
        if bron.name.startswith("chat-") and bron.name.endswith(".json"):
            return [bron]
        return []
    if bron.is_dir():
        return sorted(bron.glob("chat-*.json"))
    return []


def score_mistral(bron: Path) -> float:
    """Geef een kenmerkscore voor het mistral-formaat."""
    score = 0.0
    if bron.is_dir() and bron.name.startswith("chat-export-"):
        score += 10.0
    elif bron.is_file() and bron.name.startswith("chat-") and bron.name.endswith(".json"):
        score += 8.0
    bestanden = _vind_chat_bestanden(bron)
    if bestanden:
        score += 5.0
    for pad in bestanden[:3]:
        try:
            data = _laad_json(pad)
        except ParseFout:
            continue
        if not (isinstance(data, list) and data and isinstance(data[0], dict)):
            continue
        if "role" in data[0] and "createdAt" in data[0]:
            score += 3.0
            break
    return score


def _parse_mistral_bestand(pad: Path) -> Gesprek:
    """Parse één mistral chat-<uuid>.json bestand naar een canoniek gesprek."""
    data = _laad_json(pad)
    if not isinstance(data, list):
        raise ParseFout(f"'{pad.name}' moet een lijst van berichten zijn")
    # Een leeg chat-bestand is een gesprek zonder berichten.
    gesprek_id: str | None = None
    berichten: list[Bericht] = []
    for item in data:
        if not isinstance(item, dict):
            raise ParseFout(f"'{pad.name}' bevat een bericht dat geen object is")
        rol = item.get("role")
        if not isinstance(rol, str) or rol not in _ROLLEN:
            raise ParseFout(f"onbekende rol in '{pad.name}': {rol!r}")
        chat_id = item.get("chatId")
        if gesprek_id is None and isinstance(chat_id, str):
            gesprek_id = chat_id
        berichten.append(
            Bericht(
                id=_opt_tekst(item.get("id")),
                rol=rol,
                inhoud=_tekst(item.get("content")),
                created_at=_tijdstip(item.get("createdAt")),
                model=None,
            )
        )
    if gesprek_id is None:
        gesprek_id = pad.stem.removeprefix("chat-")
    tijden: list[float | str] = []
    for bericht in berichten:
        if bericht.created_at is not None:
            tijden.append(bericht.created_at)
    return Gesprek(
        id=gesprek_id,
        titel=None,
        provider="mistral",
        created_at=min(tijden) if tijden else None,
        berichten=_sorteer_berichten(berichten),
    )


def parse_mistral_export(bron: Path) -> list[Gesprek]:
    """Parse een mistral chat-export map naar het canonieke model."""
    bestanden = _vind_chat_bestanden(bron)
    if not bestanden:
        raise ParseFout("geen chat-*.json bestanden gevonden")
    return [_parse_mistral_bestand(pad) for pad in bestanden]

