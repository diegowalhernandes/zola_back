from fastapi import APIRouter
from app.api import auth, categories, professionals, reviews, requests, messages, uploads, appointments, webhooks


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(appointments.router)
api_router.include_router(webhooks.router)
api_router.include_router(professionals.router)
api_router.include_router(reviews.router)
api_router.include_router(requests.router)
api_router.include_router(messages.router)
api_router.include_router(uploads.router)