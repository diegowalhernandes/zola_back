"""Regras de disponibilidade: diarista (turnos) vs babá (horários)."""

from __future__ import annotations

import re
from datetime import date

from fastapi import HTTPException

DIARISTA_TURNS = frozenset({"dia_inteiro", "manha", "tarde"})
TURN_ORDER = ("manha", "tarde", "dia_inteiro")
HOURLY_SLOT_PATTERN = re.compile(r"^\d{2}:\d{2}$")

DIARISTA_DEFAULT_AVAILABILITY: dict[str, list[str]] = {
    "monday": ["manha", "tarde"],
    "tuesday": ["manha", "tarde"],
    "wednesday": ["manha", "tarde"],
    "thursday": ["manha", "tarde"],
    "friday": ["manha", "tarde"],
    "saturday": ["manha"],
    "sunday": [],
}

BABA_DEFAULT_AVAILABILITY: dict[str, list[str]] = {
    "monday": ["08:00", "09:00", "14:00"],
    "tuesday": ["08:00", "09:00", "14:00"],
    "wednesday": ["08:00", "14:00"],
    "thursday": ["08:00", "09:00", "14:00"],
    "friday": ["08:00", "14:00"],
    "saturday": ["09:00", "10:00"],
    "sunday": [],
}

TURN_LABELS = {
    "manha": "Manhã",
    "tarde": "Tarde",
    "dia_inteiro": "Dia inteiro",
}


def is_diarista(professional_type: str | None) -> bool:
    return professional_type == "diarista"


def default_availability(professional_type: str | None) -> dict[str, list[str]]:
    if is_diarista(professional_type):
        return {day: list(slots) for day, slots in DIARISTA_DEFAULT_AVAILABILITY.items()}
    return {day: list(slots) for day, slots in BABA_DEFAULT_AVAILABILITY.items()}


def uses_hourly_slots(professional_type: str | None) -> bool:
    return not is_diarista(professional_type)


def sort_slots(slots: list[str], professional_type: str | None) -> list[str]:
    if is_diarista(professional_type):
        order = {slot: index for index, slot in enumerate(TURN_ORDER)}
        return sorted(slots, key=lambda slot: order.get(slot, 99))
    return sorted(slots)


def weekly_has_hourly_slots(weekly: dict[str, list[str]]) -> bool:
    for slots in weekly.values():
        for slot in slots:
            if HOURLY_SLOT_PATTERN.match(slot):
                return True
    return False


def normalize_weekly_availability(
    weekly: dict[str, list[str]] | None,
    professional_type: str | None,
) -> dict[str, list[str]]:
    if not weekly:
        return default_availability(professional_type)

    if is_diarista(professional_type) and weekly_has_hourly_slots(weekly):
        return default_availability("diarista")

    if is_diarista(professional_type):
        normalized: dict[str, list[str]] = {}
        for day, slots in weekly.items():
            valid = [slot for slot in slots if slot in DIARISTA_TURNS]
            normalized[day] = sort_slots(valid, "diarista")
        return normalized

    normalized = {}
    for day, slots in weekly.items():
        valid = [slot for slot in slots if HOURLY_SLOT_PATTERN.match(slot)]
        normalized[day] = sort_slots(valid, "baba")
    return normalized


def blocked_diarista_turns(taken: set[str]) -> set[str]:
    blocked = set(taken)
    if "dia_inteiro" in taken:
        blocked.update(DIARISTA_TURNS)
        return blocked

    if "manha" in taken:
        blocked.add("dia_inteiro")
    if "tarde" in taken:
        blocked.add("dia_inteiro")
    if "manha" in taken and "tarde" in taken:
        blocked.update(DIARISTA_TURNS)
    return blocked


def free_diarista_slots(base_slots: list[str], taken: set[str]) -> list[str]:
    blocked = blocked_diarista_turns(taken)
    return [slot for slot in base_slots if slot not in blocked]


def validate_diarista_batch(slots: list[tuple[date, str]]) -> None:
    by_date: dict[date, set[str]] = {}
    for appointment_date, time_slot in slots:
        if time_slot not in DIARISTA_TURNS:
            raise HTTPException(status_code=400, detail="Turno inválido para diarista")
        by_date.setdefault(appointment_date, set()).add(time_slot)

    for appointment_date, day_slots in by_date.items():
        if len(day_slots) > 1:
            raise HTTPException(
                status_code=400,
                detail="Para diarista, selecione apenas um turno por dia",
            )


def format_slot_label(time_slot: str, professional_type: str | None = None) -> str:
    if is_diarista(professional_type) or time_slot in TURN_LABELS:
        return TURN_LABELS.get(time_slot, time_slot)
    return time_slot
