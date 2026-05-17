from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User, Professional
from app.schemas.schemas import UserCreate, LoginInput, Token
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=Token)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    user_exists = db.query(User).filter(User.email == payload.email).first()

    if user_exists:
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    if payload.role == "professional":
        professional = Professional(
            user_id=user.id,
            category_id=1,
            title=f"{user.name} - Serviços gerais",
            description="Novo profissional cadastrado na plataforma.",
            city="Santos",
            state="SP",
            price_from=0,
            rating=5,
            reviews_count=0,
            whatsapp="",
            is_featured=True,
            image=None,
            latitude=None,
            longitude=None,
        )

        db.add(professional)
        db.commit()
        db.refresh(professional)

    token = create_access_token({"sub": str(user.id), "role": user.role})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    }


@router.post("/login")
def login(payload: LoginInput, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    token = create_access_token({"sub": str(user.id), "role": user.role})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    }