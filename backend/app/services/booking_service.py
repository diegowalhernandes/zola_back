from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Appointment, Professional, User
from app.services.slot_rules import (
    blocked_diarista_turns,
    is_diarista,
    uses_hourly_slots,
    validate_diarista_batch,
)
from app.utils.json_fields import loads_json

WEEKDAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
BLOCKING_STATUSES = ["awaiting_payment", "pending", "confirmed"]


def _taken_slots_for_day(
    db: Session,
    professional_id: int,
    appointment_date: date,
    *,
    exclude_slot: str | None = None,
) -> set[str]:
    rows = (
        db.query(Appointment.time_slot)
        .filter(
            Appointment.professional_id == professional_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status.in_(BLOCKING_STATUSES),
        )
        .all()
    )
    taken = {row[0] for row in rows}
    if exclude_slot:
        taken.discard(exclude_slot)
    return taken


def validate_booking_slot(
    db: Session,
    professional: Professional,
    appointment_date: date,
    time_slot: str,
) -> None:
    weekly = loads_json(professional.availability) or {}
    weekday_key = WEEKDAY_KEYS[appointment_date.weekday()]
    allowed_slots = weekly.get(weekday_key, [])

    if time_slot not in allowed_slots:
        detail = "Turno indisponível para este dia" if is_diarista(professional.professional_type) else "Horário indisponível para este dia"
        raise HTTPException(status_code=400, detail=detail)

    taken = _taken_slots_for_day(db, professional.id, appointment_date)

    if is_diarista(professional.professional_type):
        if time_slot in blocked_diarista_turns(taken):
            raise HTTPException(status_code=409, detail="Este turno já foi reservado")
        return

    if time_slot in taken:
        raise HTTPException(status_code=409, detail="Este horário já foi reservado")


def validate_booking_batch(
    professional: Professional,
    slots: list[tuple[date, str]],
) -> None:
    if is_diarista(professional.professional_type):
        validate_diarista_batch(slots)
        return

    if not uses_hourly_slots(professional.professional_type):
        return

    seen: set[tuple[date, str]] = set()
    for appointment_date, time_slot in slots:
        key = (appointment_date, time_slot)
        if key in seen:
            raise HTTPException(status_code=400, detail="Horário duplicado na solicitação")
        seen.add(key)


def require_client(user: User) -> None:
    if user.role != "client":
        raise HTTPException(status_code=403, detail="Somente clientes podem agendar horários")
