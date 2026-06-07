"""Normalização de texto para persistência (minúsculas + typos comuns em PT-BR)."""
from __future__ import annotations

import re
from typing import Any

# Palavras isoladas frequentemente digitadas errado
WORD_FIXES: dict[str, str] = {
    "babaa": "baba",
    "baaba": "baba",
    "diarisa": "diarista",
    "diaritsa": "diarista",
    "diarista": "diarista",
    "profisional": "profissional",
    "profissonal": "profissional",
    "profissional": "profissional",
    "experiêcnia": "experiencia",
    "experiencia": "experiencia",
    "santtos": "santos",
    "santos": "santos",
    "vicente": "vicente",
    "limpeza": "limpeza",
    "residencial": "residencial",
    "residensial": "residencial",
    "comercial": "comercial",
    "crianca": "crianca",
    "criança": "crianca",
    "criancas": "criancas",
    "crianças": "criancas",
}

# Expressões com mais de uma palavra
PHRASE_FIXES: list[tuple[str, str]] = [
    (r"\bsao paulo\b", "são paulo"),
    (r"\bsao vicente\b", "são vicente"),
    (r"\bpraia grande\b", "praia grande"),
    (r"\bpos obra\b", "pós-obra"),
    (r"\bpos-obra\b", "pós-obra"),
]


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def fix_typos(text: str) -> str:
    normalized = collapse_whitespace(text).lower()
    for pattern, replacement in PHRASE_FIXES:
        normalized = re.sub(pattern, replacement, normalized)
    return " ".join(WORD_FIXES.get(word, word) for word in normalized.split(" "))


def normalize_email(value: str) -> str:
    return collapse_whitespace(value).lower()


def normalize_name(value: str) -> str:
    return fix_typos(value)


def normalize_free_text(value: str) -> str:
    return fix_typos(value)


def normalize_city(value: str) -> str:
    return fix_typos(value)


def normalize_state(value: str) -> str:
    letters = re.sub(r"[^a-zA-Z]", "", value)
    return letters.lower()[:2]


def normalize_professional_type(value: str) -> str:
    fixed = fix_typos(value)
    if fixed in {"baba", "babá"}:
        return "baba"
    if fixed.startswith("diar"):
        return "diarista"
    return fixed


def normalize_job_specs(specs: dict[str, Any] | None) -> dict[str, Any] | None:
    if not specs:
        return specs

    result: dict[str, Any] = {}
    for key, value in specs.items():
        if isinstance(value, str):
            result[key] = fix_typos(value)
        elif isinstance(value, list):
            result[key] = [fix_typos(item) if isinstance(item, str) else item for item in value]
        else:
            result[key] = value
    return result

