from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
        }
    return {
        "pool_pre_ping": True,
        "connect_args": {"connect_timeout": 10},
    }


engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
