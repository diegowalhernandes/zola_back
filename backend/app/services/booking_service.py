from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Appointment, Professional, User
from app.utils.json_fields import loads_json

WEEKDAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
BLOCKING_STATUSES = ["awaiting_payment", "pending", "confirmed"]


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
        raise HTTPException(status_code=400, detail="Horário indisponível para este dia")

    conflict = (
        db.query(Appointment)
        .filter(
            Appointment.professional_id == professional.id,
            Appointment.appointment_date == appointment_date,
            Appointment.time_slot == time_slot,
            Appointment.status.in_(BLOCKING_STATUSES),
        )
        .first()
    )
    if conflict:
        raise HTTPException(status_code=409, detail="Este horário já foi reservado")


def require_client(user: User) -> None:
    if user.role != "client":
        raise HTTPException(status_code=403, detail="Somente clientes podem agendar horários")
