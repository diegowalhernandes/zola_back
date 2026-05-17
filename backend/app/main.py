from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette import status
import os

from app.api.router import api_router
from app.core.config import settings
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
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

if settings.FRONTEND_ORIGIN:
    allowed_origins += [origin.strip() for origin in settings.FRONTEND_ORIGIN.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        f"{'.'.join(str(loc) for loc in err['loc'][1:])}: {err['msg']}"
        for err in exc.errors()
    ]

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Dados inválidos: " + "; ".join(errors)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno do servidor. Tente novamente mais tarde."},
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