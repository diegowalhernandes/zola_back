from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.models import Appointment, Professional
from app.schemas.schemas import DayAvailability
from app.utils.json_fields import loads_json

WEEKDAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def get_day_availability(
    db: Session,
    professional: Professional,
    start: date,
    end: date,
) -> list[DayAvailability]:
    weekly = loads_json(professional.availability) or {}
    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.professional_id == professional.id,
            Appointment.appointment_date >= start,
            Appointment.appointment_date <= end,
            Appointment.status.in_(["pending", "confirmed"]),
        )
        .all()
    )

    booked: dict[str, set[str]] = {}
    for item in appointments:
        key = item.appointment_date.isoformat()
        booked.setdefault(key, set()).add(item.time_slot)

    result: list[DayAvailability] = []
    current = start
    while current <= end:
        weekday_key = WEEKDAY_KEYS[current.weekday()]
        base_slots = weekly.get(weekday_key, [])
        taken = booked.get(current.isoformat(), set())
        free_slots = [slot for slot in base_slots if slot not in taken]
        if free_slots:
            result.append(DayAvailability(date=current, slots=free_slots))
        current += timedelta(days=1)

    return result
