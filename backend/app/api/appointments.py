from datetime import date, timedelta
from uuid import uuid4

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query
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
    BatchCheckoutCreate,
    BatchCheckoutOut,
    DayAvailability,
    DepositPreviewOut,
    SlotSelection,
)
from app.services.availability_service import expire_stale_payment_holds, get_day_availability
from app.services.booking_service import require_client, validate_booking_slot
from app.services.payment_service import (
    calculate_batch_amounts,
    calculate_booking_amounts,
    cancel_awaiting_payment,
    cancel_batch_awaiting,
    create_stripe_batch_checkout,
    create_stripe_checkout,
    payments_enabled,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


def _build_list_item(
    appointment: Appointment,
    *,
    professional_name: str | None = None,
    client_name: str | None = None,
) -> AppointmentListItem:
    return AppointmentListItem(
        id=appointment.id,
        professional_id=appointment.professional_id,
        client_id=appointment.client_id,
        appointment_date=appointment.appointment_date,
        time_slot=appointment.time_slot,
        status=appointment.status,
        total_amount=appointment.total_amount,
        deposit_amount=appointment.deposit_amount,
        amount_due=appointment.amount_due,
        deposit_paid=appointment.deposit_paid,
        payment_status=appointment.payment_status,
        payment_mode=appointment.payment_mode,
        batch_id=appointment.batch_id,
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
def deposit_preview(
    professional_id: int,
    slots: int = Query(1, ge=1, le=20),
    db: Session = Depends(get_db),
):
    professional = db.get(Professional, professional_id)
    if not professional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    total_amount, deposit_amount, _ = calculate_batch_amounts(professional.price_from, slots, "deposit")
    enabled = payments_enabled() and not settings.PAYMENTS_MOCK

    return DepositPreviewOut(
        total_amount=total_amount,
        deposit_amount=deposit_amount,
        deposit_percent=settings.BOOKING_DEPOSIT_PERCENT,
        payments_enabled=enabled,
        slot_count=slots,
    )


@router.post("/checkout-batch", response_model=BatchCheckoutOut)
def checkout_batch(
    data: BatchCheckoutCreate,
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

    seen: set[tuple[date, str]] = set()
    for slot in data.slots:
        key = (slot.appointment_date, slot.time_slot)
        if key in seen:
            raise HTTPException(status_code=400, detail="Horário duplicado na solicitação")
        seen.add(key)
        validate_booking_slot(db, professional, slot.appointment_date, slot.time_slot)

    unit_total, unit_deposit = calculate_booking_amounts(professional.price_from)
    total_amount, deposit_amount, amount_due = calculate_batch_amounts(
        professional.price_from,
        len(data.slots),
        data.payment_mode,
    )
    use_payments = payments_enabled() and not settings.PAYMENTS_MOCK
    batch_id = str(uuid4())
    per_slot_due = round(amount_due / len(data.slots), 2)

    appointments: list[Appointment] = []
    for slot in data.slots:
        appointment = Appointment(
            professional_id=data.professional_id,
            client_id=user.id,
            appointment_date=slot.appointment_date,
            time_slot=slot.time_slot,
            notes=data.notes,
            status="awaiting_payment" if use_payments else "confirmed",
            total_amount=unit_total,
            deposit_amount=unit_deposit,
            amount_due=per_slot_due,
            deposit_paid=not use_payments,
            payment_status="pending" if use_payments else "paid",
            payment_mode=data.payment_mode,
            batch_id=batch_id,
        )
        db.add(appointment)
        appointments.append(appointment)

    db.commit()
    for appointment in appointments:
        db.refresh(appointment)

    if not use_payments:
        return BatchCheckoutOut(
            batch_id=batch_id,
            appointment_ids=[item.id for item in appointments],
            checkout_url=None,
            total_amount=total_amount,
            amount_due=amount_due,
            deposit_amount=deposit_amount,
            payment_mode=data.payment_mode,
            payments_required=False,
            status="confirmed",
        )

    try:
        session = create_stripe_batch_checkout(
            appointments=appointments,
            professional=professional,
            client=user,
            amount_due=amount_due,
            payment_mode=data.payment_mode,
            batch_id=batch_id,
        )
    except stripe.StripeError as exc:
        for appointment in appointments:
            db.delete(appointment)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Falha ao iniciar pagamento: {exc.user_message or str(exc)}") from exc

    for appointment in appointments:
        appointment.stripe_checkout_session_id = session.id
    db.commit()

    return BatchCheckoutOut(
        batch_id=batch_id,
        appointment_ids=[item.id for item in appointments],
        checkout_url=session.url,
        total_amount=total_amount,
        amount_due=amount_due,
        deposit_amount=deposit_amount,
        payment_mode=data.payment_mode,
        payments_required=True,
        status="awaiting_payment",
    )


@router.post("/checkout", response_model=AppointmentCheckoutOut)
def checkout_appointment(
    data: AppointmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    batch = checkout_batch(
        BatchCheckoutCreate(
            professional_id=data.professional_id,
            slots=[SlotSelection(appointment_date=data.appointment_date, time_slot=data.time_slot)],
            notes=data.notes,
            payment_mode="deposit",
        ),
        user,
        db,
    )
    return AppointmentCheckoutOut(
        appointment_id=batch.appointment_ids[0],
        checkout_url=batch.checkout_url,
        deposit_amount=batch.deposit_amount,
        total_amount=batch.total_amount,
        payments_required=batch.payments_required,
        status=batch.status,
    )


@router.post("/batch/{batch_id}/cancel-awaiting")
def cancel_batch(
    batch_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cancelled = cancel_batch_awaiting(db, batch_id, user.id)
    if cancelled == 0 and user.role != "admin":
        raise HTTPException(status_code=404, detail="Reserva não encontrada ou já finalizada")
    return {"ok": True, "cancelled": cancelled}


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

    if appointment.batch_id:
        cancel_batch_awaiting(db, appointment.batch_id, user.id)
    else:
        cancel_awaiting_payment(db, appointment)
    return {"ok": True, "status": "cancelled"}


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
            Appointment.status.in_(["confirmed", "awaiting_payment"]),
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
