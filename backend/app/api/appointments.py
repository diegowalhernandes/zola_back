from datetime import date, timedelta

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_professional
from app.core.config import settings
from app.db.session import get_db
from app.models.models import Appointment, Professional, User
from app.schemas.schemas import (
    AppointmentCheckoutOut,
    AppointmentCreate,
    AppointmentListItem,
    AppointmentOut,
    DayAvailability,
    DepositPreviewOut,
)
from app.services.availability_service import expire_stale_payment_holds, get_day_availability
from app.services.booking_service import require_client, validate_booking_slot
from app.services.payment_service import (
    calculate_booking_amounts,
    cancel_awaiting_payment,
    create_stripe_checkout,
    mark_appointment_paid,
    payments_enabled,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


def _build_list_item(appointment: Appointment, *, professional_name: str | None = None, client_name: str | None = None) -> AppointmentListItem:
    return AppointmentListItem(
        id=appointment.id,
        professional_id=appointment.professional_id,
        client_id=appointment.client_id,
        appointment_date=appointment.appointment_date,
        time_slot=appointment.time_slot,
        status=appointment.status,
        deposit_amount=appointment.deposit_amount,
        deposit_paid=appointment.deposit_paid,
        payment_status=appointment.payment_status,
        notes=appointment.notes,
        professional_name=professional_name,
        client_name=client_name,
        created_at=appointment.created_at,
    )


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


@router.get("/deposit-preview/{professional_id}", response_model=DepositPreviewOut)
def deposit_preview(professional_id: int, db: Session = Depends(get_db)):
    professional = db.get(Professional, professional_id)
    if not professional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    total_amount, deposit_amount = calculate_booking_amounts(professional.price_from)
    enabled = payments_enabled() and not settings.PAYMENTS_MOCK

    return DepositPreviewOut(
        total_amount=total_amount,
        deposit_amount=deposit_amount,
        deposit_percent=settings.BOOKING_DEPOSIT_PERCENT,
        payments_enabled=enabled,
    )


@router.post("/checkout", response_model=AppointmentCheckoutOut)
def checkout_appointment(
    data: AppointmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_client(user)

    professional = (
        db.query(Professional)
        .options(joinedload(Professional.user))
        .filter(Professional.id == data.professional_id)
        .first()
    )
    if not professional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    expire_stale_payment_holds(db)
    validate_booking_slot(db, professional, data.appointment_date, data.time_slot)

    total_amount, deposit_amount = calculate_booking_amounts(professional.price_from)
    use_payments = payments_enabled() and not settings.PAYMENTS_MOCK

    appointment = Appointment(
        professional_id=data.professional_id,
        client_id=user.id,
        appointment_date=data.appointment_date,
        time_slot=data.time_slot,
        notes=data.notes,
        status="awaiting_payment" if use_payments else "confirmed",
        total_amount=total_amount,
        deposit_amount=deposit_amount,
        deposit_paid=not use_payments,
        payment_status="pending" if use_payments else "paid",
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    if not use_payments:
        return AppointmentCheckoutOut(
            appointment_id=appointment.id,
            checkout_url=None,
            deposit_amount=deposit_amount,
            total_amount=total_amount,
            payments_required=False,
            status=appointment.status,
        )

    try:
        session = create_stripe_checkout(
            appointment=appointment,
            professional=professional,
            client=user,
        )
    except stripe.StripeError as exc:
        db.delete(appointment)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Falha ao iniciar pagamento: {exc.user_message or str(exc)}") from exc

    appointment.stripe_checkout_session_id = session.id
    db.commit()

    return AppointmentCheckoutOut(
        appointment_id=appointment.id,
        checkout_url=session.url,
        deposit_amount=deposit_amount,
        total_amount=total_amount,
        payments_required=True,
        status=appointment.status,
    )


@router.post("/{appointment_id}/cancel-awaiting")
def cancel_awaiting(
    appointment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    if appointment.client_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Sem permissão")
    if appointment.status != "awaiting_payment":
        raise HTTPException(status_code=400, detail="Agendamento não está aguardando pagamento")

    cancel_awaiting_payment(db, appointment)
    return {"ok": True, "status": appointment.status}


@router.get("/me", response_model=list[AppointmentListItem])
def list_my_appointments(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_client(user)
    expire_stale_payment_holds(db)

    rows = (
        db.query(Appointment)
        .options(joinedload(Appointment.professional).joinedload(Professional.user))
        .filter(Appointment.client_id == user.id)
        .order_by(Appointment.appointment_date.desc(), Appointment.time_slot.desc())
        .all()
    )

    return [
        _build_list_item(
            item,
            professional_name=item.professional.user.name if item.professional and item.professional.user else None,
        )
        for item in rows
    ]


@router.get("/incoming", response_model=list[AppointmentListItem])
def list_incoming_appointments(
    user: User = Depends(require_professional),
    db: Session = Depends(get_db),
):
    expire_stale_payment_holds(db)
    professional = db.query(Professional).filter(Professional.user_id == user.id).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Perfil profissional não encontrado")

    rows = (
        db.query(Appointment)
        .options(joinedload(Appointment.professional))
        .filter(
            Appointment.professional_id == professional.id,
            Appointment.status.in_(["confirmed", "pending"]),
            Appointment.deposit_paid.is_(True),
        )
        .order_by(Appointment.appointment_date.asc(), Appointment.time_slot.asc())
        .all()
    )

    clients = {
        client.id: client.name
        for client in db.query(User).filter(User.id.in_([row.client_id for row in rows] or [0])).all()
    }

    return [
        _build_list_item(item, client_name=clients.get(item.client_id))
        for item in rows
    ]


@router.post("", response_model=AppointmentOut, deprecated=True)
def create_appointment(
    data: AppointmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    checkout = checkout_appointment(data, user, db)
    appointment = db.get(Appointment, checkout.appointment_id)
    if not appointment:
        raise HTTPException(status_code=500, detail="Agendamento não encontrado após checkout")
    return appointment
