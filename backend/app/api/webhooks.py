import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.models import Appointment
from app.services.payment_service import mark_appointment_paid

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.STRIPE_WEBHOOK_SECRET.strip():
        raise HTTPException(status_code=503, detail="Webhook Stripe não configurado")

    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Assinatura Stripe ausente")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Payload inválido") from exc
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Assinatura inválida") from exc

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        appointment_id = session.get("metadata", {}).get("appointment_id")
        if appointment_id:
            appointment = db.get(Appointment, int(appointment_id))
            if appointment and appointment.status == "awaiting_payment":
                mark_appointment_paid(db, appointment, session)

    if event["type"] == "checkout.session.expired":
        session = event["data"]["object"]
        appointment_id = session.get("metadata", {}).get("appointment_id")
        if appointment_id:
            appointment = db.get(Appointment, int(appointment_id))
            if appointment and appointment.status == "awaiting_payment":
                appointment.status = "cancelled"
                appointment.payment_status = "expired"
                db.commit()

    return {"received": True}
