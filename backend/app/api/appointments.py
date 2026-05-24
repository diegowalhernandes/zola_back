from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import Appointment, Professional, User
from app.schemas.schemas import AppointmentCreate, AppointmentOut, DayAvailability
from app.services.availability_service import get_day_availability
from app.utils.json_fields import loads_json

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/professional/{professional_id}/availability", response_model=list[DayAvailability])
def list_availability(
    professional_id: int,
    from_date: date = Query(alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
):
    professional = db.get(Professional, professional_id)
    if not professional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    end = to_date or (from_date + timedelta(days=30))
    if end < from_date:
        raise HTTPException(status_code=400, detail="Data final inválida")

    return get_day_availability(db, professional, from_date, end)


@router.post("", response_model=AppointmentOut)
def create_appointment(
    data: AppointmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "client":
        raise HTTPException(status_code=403, detail="Somente clientes podem agendar horários")

    professional = db.get(Professional, data.professional_id)
    if not professional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    weekly = loads_json(professional.availability) or {}
    weekday_key = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][
        data.appointment_date.weekday()
    ]
    allowed_slots = weekly.get(weekday_key, [])

    if data.time_slot not in allowed_slots:
        raise HTTPException(status_code=400, detail="Horário indisponível para este dia")

    conflict = (
        db.query(Appointment)
        .filter(
            Appointment.professional_id == data.professional_id,
            Appointment.appointment_date == data.appointment_date,
            Appointment.time_slot == data.time_slot,
            Appointment.status.in_(["pending", "confirmed"]),
        )
        .first()
    )
    if conflict:
        raise HTTPException(status_code=409, detail="Este horário já foi reservado")

    appointment = Appointment(
        professional_id=data.professional_id,
        client_id=user.id,
        appointment_date=data.appointment_date,
        time_slot=data.time_slot,
        notes=data.notes,
        status="pending",
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment
