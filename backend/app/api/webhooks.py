import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.models import Appointment
from app.services.payment_service import expire_batch_awaiting, mark_checkout_paid

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
        metadata = session.get("metadata", {})
        mark_checkout_paid(db, session, metadata)

    if event["type"] == "checkout.session.expired":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        batch_id = metadata.get("batch_id")
        if batch_id:
            expire_batch_awaiting(db, batch_id)
        elif metadata.get("appointment_id"):
            appointment = db.get(Appointment, int(metadata["appointment_id"]))
            if appointment and appointment.status == "awaiting_payment":
                appointment.status = "cancelled"
                appointment.payment_status = "expired"
                db.commit()

    return {"received": True}
