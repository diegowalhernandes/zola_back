from __future__ import annotations

import stripe
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Appointment, Professional, User


def calculate_booking_amounts(price_from: float) -> tuple[float, float]:
    total = max(float(price_from or 0), settings.BOOKING_MIN_TOTAL_BRL)
    deposit = total * (settings.BOOKING_DEPOSIT_PERCENT / 100)
    deposit = max(deposit, settings.BOOKING_DEPOSIT_MIN_BRL)
    deposit = min(deposit, total)
    return round(total, 2), round(deposit, 2)


def calculate_batch_amounts(price_from: float, slot_count: int, payment_mode: str) -> tuple[float, float, float]:
    unit_total, unit_deposit = calculate_booking_amounts(price_from)
    count = max(1, slot_count)
    total_amount = round(unit_total * count, 2)
    deposit_amount = round(unit_deposit * count, 2)
    amount_due = total_amount if payment_mode == "full" else deposit_amount
    return total_amount, deposit_amount, amount_due


def payments_enabled() -> bool:
    return settings.payments_configured


def create_stripe_checkout(
    *,
    appointment: Appointment,
    professional: Professional,
    client: User,
) -> stripe.checkout.Session:
    _, _, amount_due = calculate_batch_amounts(professional.price_from, 1, "deposit")
    return create_stripe_batch_checkout(
        appointments=[appointment],
        professional=professional,
        client=client,
        amount_due=amount_due,
        payment_mode="deposit",
        batch_id=appointment.batch_id or str(appointment.id),
    )


def create_stripe_batch_checkout(
    *,
    appointments: list[Appointment],
    professional: Professional,
    client: User,
    amount_due: float,
    payment_mode: str,
    batch_id: str,
) -> stripe.checkout.Session:
    if not payments_enabled():
        raise HTTPException(
            status_code=503,
            detail="Pagamentos não configurados. Defina STRIPE_SECRET_KEY no servidor.",
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY
    amount_cents = int(round(amount_due * 100))

    if amount_cents < 50:
        raise HTTPException(status_code=400, detail="Valor do pagamento inválido para cobrança.")

    frontend = settings.frontend_base_url
    professional_name = professional.user.name if professional.user else professional.title
    slot_count = len(appointments)
    payment_label = "pagamento integral" if payment_mode == "full" else f"sinal ({int(settings.BOOKING_DEPOSIT_PERCENT)}%)"
    slots_summary = ", ".join(
        f"{item.appointment_date.strftime('%d/%m')} {item.time_slot}" for item in appointments[:3]
    )
    if slot_count > 3:
        slots_summary += f" +{slot_count - 3}"

    return stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "brl",
                    "unit_amount": amount_cents,
                    "product_data": {
                        "name": f"Agendamento — {professional_name}",
                        "description": f"{slot_count} horário(s) · {payment_label} · {slots_summary}",
                    },
                },
                "quantity": 1,
            }
        ],
        metadata={
            "batch_id": batch_id,
            "appointment_ids": ",".join(str(item.id) for item in appointments),
            "payment_mode": payment_mode,
            "appointment_id": str(appointments[0].id),
        },
        success_url=f"{frontend}/agendamento/sucesso?batch_id={batch_id}",
        cancel_url=f"{frontend}/agendamento/cancelado?batch_id={batch_id}",
        customer_email=client.email,
    )


def mark_appointment_paid(db: Session, appointment: Appointment, session) -> None:
    metadata = session.get("metadata", {}) if isinstance(session, dict) else dict(session.metadata or {})
    mark_checkout_paid(db, session, metadata)


def mark_checkout_paid(db: Session, session, metadata: dict) -> None:
    session_id = session["id"] if isinstance(session, dict) else session.id
    payment_intent = session.get("payment_intent") if isinstance(session, dict) else session.payment_intent
    payment_mode = metadata.get("payment_mode", "deposit")

    rows: list[Appointment] = []
    batch_id = metadata.get("batch_id")
    if batch_id:
        rows = (
            db.query(Appointment)
            .filter(Appointment.batch_id == batch_id, Appointment.status == "awaiting_payment")
            .all()
        )

    if not rows and metadata.get("appointment_ids"):
        ids = [int(value) for value in metadata["appointment_ids"].split(",") if value.strip().isdigit()]
        rows = (
            db.query(Appointment)
            .filter(Appointment.id.in_(ids), Appointment.status == "awaiting_payment")
            .all()
        )

    if not rows and metadata.get("appointment_id"):
        appointment = db.get(Appointment, int(metadata["appointment_id"]))
        if appointment and appointment.status == "awaiting_payment":
            rows = [appointment]

    for appointment in rows:
        appointment.status = "confirmed"
        appointment.deposit_paid = True
        appointment.payment_status = "paid"
        appointment.payment_mode = payment_mode
        appointment.stripe_checkout_session_id = str(session_id or "")
        appointment.stripe_payment_intent_id = str(payment_intent or "")

    if rows:
        db.commit()


def cancel_awaiting_payment(db: Session, appointment: Appointment) -> None:
    if appointment.status != "awaiting_payment":
        return
    appointment.status = "cancelled"
    appointment.payment_status = "cancelled"
    db.commit()


def cancel_batch_awaiting(db: Session, batch_id: str, client_id: int) -> int:
    rows = (
        db.query(Appointment)
        .filter(
            Appointment.batch_id == batch_id,
            Appointment.client_id == client_id,
            Appointment.status == "awaiting_payment",
        )
        .all()
    )
    for appointment in rows:
        appointment.status = "cancelled"
        appointment.payment_status = "cancelled"
    if rows:
        db.commit()
    return len(rows)


def expire_batch_awaiting(db: Session, batch_id: str) -> None:
    rows = (
        db.query(Appointment)
        .filter(Appointment.batch_id == batch_id, Appointment.status == "awaiting_payment")
        .all()
    )
    for appointment in rows:
        appointment.status = "cancelled"
        appointment.payment_status = "expired"
    if rows:
        db.commit()
