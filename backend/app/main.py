from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.router import api_router
from app.db.session import Base, engine
from app.db.seed import seed_database

app = FastAPI(
    title="Zola Serviços API",
    version="1.0.0"
)

# =========================
# Pastas
# =========================
os.makedirs("uploads", exist_ok=True)

app.mount(
    "/media",
    StaticFiles(directory="uploads"),
    name="media"
)

# =========================
# CORS
# =========================
frontend_origin = os.getenv(
    "FRONTEND_ORIGIN",
    "https://zola-front-hbgt.vercel.app"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        frontend_origin,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Rotas
# =========================
app.include_router(api_router)

# =========================
# Startup
# =========================
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed_database()

# =========================
# Healthcheck
# =========================
@app.get("/")
def root():
    return {
        "status": "online",
        "app": "Zola Serviços API"
    }