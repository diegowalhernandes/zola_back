from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError
from starlette import status
import logging
import os

from app.api.router import api_router
from app.core.config import settings
from app.db.session import Base, engine
from app.db.seed import ensure_default_availability, ensure_extra_categories, seed_database
from app.db.migrate import run_migrations

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
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
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
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# =========================
# Startup
# =========================
logger = logging.getLogger(__name__)


@app.on_event("startup")
def on_startup():
    try:
        Base.metadata.create_all(bind=engine)
        run_migrations(engine)
        seed_database()
        ensure_extra_categories()
        ensure_default_availability()
    except OperationalError as exc:
        db_target = settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url
        logger.error("Falha ao conectar no banco (%s): %s", db_target, exc)
        detail = str(exc).lower()
        if "tenant/user" in detail or "enotfound" in detail:
            hint = (
                "Supabase rejeitou o usuário do pooler (tenant/user not found). "
                "No painel Supabase → Project Settings → Database, copie de novo a URI "
                "(Transaction pooler, porta 6543). Confirme que o projeto não está pausado, "
                "que o usuário é postgres.SEU_PROJECT_REF e que a senha na URL está correta "
                "(caracteres especiais: $ → %24). Use postgresql+psycopg:// no início."
            )
        else:
            hint = (
                "Verifique DATABASE_URL no Render. Local: sqlite:///./zola.db. "
                "Senhas com $ na URL precisam ser %24."
            )
        raise RuntimeError(f"Não foi possível conectar ao banco de dados. {hint}") from exc

# =========================
# Healthcheck
# =========================
@app.get("/")
def root():
    return {
        "status": "online",
        "app": "Zola Serviços API",
        "api": settings.API_V1_PREFIX,
        "docs": "/docs",
        "storage": {
            "supabase_configured": settings.supabase_storage_configured,
            "public_api_base_url": settings.public_api_base_url,
        },
        "payments": {
            "stripe_configured": settings.payments_configured,
            "deposit_percent": settings.BOOKING_DEPOSIT_PERCENT,
            "payments_mock": settings.PAYMENTS_MOCK,
        },
    }