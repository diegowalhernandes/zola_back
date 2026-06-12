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


def payments_enabled() -> bool:
    return settings.payments_configured


def create_stripe_checkout(
    *,
    appointment: Appointment,
    professional: Professional,
    client: User,
) -> stripe.checkout.Session:
    if not payments_enabled():
        raise HTTPException(
            status_code=503,
            detail="Pagamentos não configurados. Defina STRIPE_SECRET_KEY no servidor.",
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY
    total_amount, deposit_amount = calculate_booking_amounts(professional.price_from)
    amount_cents = int(round(deposit_amount * 100))

    if amount_cents < 50:
        raise HTTPException(status_code=400, detail="Valor do sinal inválido para cobrança.")

    frontend = settings.frontend_base_url
    professional_name = professional.user.name if professional.user else professional.title

    return stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "brl",
                    "unit_amount": amount_cents,
                    "product_data": {
                        "name": f"Sinal de agendamento — {professional_name}",
                        "description": (
                            f"{appointment.appointment_date.strftime('%d/%m/%Y')} "
                            f"às {appointment.time_slot} · "
                            f"{int(settings.BOOKING_DEPOSIT_PERCENT)}% do serviço"
                        ),
                    },
                },
                "quantity": 1,
            }
        ],
        metadata={
            "appointment_id": str(appointment.id),
            "professional_id": str(professional.id),
            "client_id": str(client.id),
        },
        success_url=f"{frontend}/agendamento/sucesso?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{frontend}/agendamento/cancelado?appointment_id={appointment.id}",
        customer_email=client.email,
    )


def mark_appointment_paid(db: Session, appointment: Appointment, session) -> None:
    session_id = session["id"] if isinstance(session, dict) else session.id
    payment_intent = session.get("payment_intent") if isinstance(session, dict) else session.payment_intent

    appointment.status = "confirmed"
    appointment.deposit_paid = True
    appointment.payment_status = "paid"
    appointment.stripe_checkout_session_id = str(session_id or "")
    appointment.stripe_payment_intent_id = str(payment_intent or "")
    db.commit()


def cancel_awaiting_payment(db: Session, appointment: Appointment) -> None:
    if appointment.status != "awaiting_payment":
        return
    appointment.status = "cancelled"
    appointment.payment_status = "cancelled"
    db.commit()
