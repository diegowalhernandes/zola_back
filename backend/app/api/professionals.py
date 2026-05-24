from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_professional
from app.db.session import get_db
from app.models.models import Professional, User
from app.schemas.schemas import ProfessionalCreate, ProfessionalOut, ProfessionalUpdate
from app.services.professional_helpers import build_professional_out
from app.utils.json_fields import dumps_json

router = APIRouter(prefix="/professionals", tags=["Professionals"])


def _apply_update(professional: Professional, data: ProfessionalUpdate) -> None:
    payload = data.model_dump(exclude_none=True)
    if "job_specs" in payload:
        payload["job_specs"] = dumps_json(payload["job_specs"])
    if "availability" in payload:
        payload["availability"] = dumps_json(payload["availability"])
    for key, value in payload.items():
        setattr(professional, key, value)


@router.get("", response_model=list[ProfessionalOut])
def list_professionals(
    category_id: int | None = None,
    professional_type: str | None = None,
    city: str | None = None,
    min_rating: float | None = Query(default=None, ge=1, le=5),
    max_price: float | None = None,
    featured: bool | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = db.query(Professional).options(joinedload(Professional.user), joinedload(Professional.category))
    if category_id:
        query = query.filter(Professional.category_id == category_id)
    if professional_type:
        query = query.filter(Professional.professional_type == professional_type)
    if city:
        query = query.filter(Professional.city.ilike(f"%{city}%"))
    if min_rating:
        query = query.filter(Professional.rating >= min_rating)
    if max_price:
        query = query.filter(Professional.price_from <= max_price)
    if featured is not None:
        query = query.filter(Professional.is_featured == featured)
    professionals = query.offset((page - 1) * limit).limit(limit).all()
    return [build_professional_out(item) for item in professionals]


@router.get("/me", response_model=ProfessionalOut)
def get_my_professional(user: User = Depends(require_professional), db: Session = Depends(get_db)):
    professional = (
        db.query(Professional)
        .options(joinedload(Professional.user), joinedload(Professional.category))
        .filter(Professional.user_id == user.id)
        .first()
    )
    if not professional:
        raise HTTPException(status_code=404, detail="Perfil profissional não encontrado")
    return build_professional_out(professional)


@router.get("/{professional_id}", response_model=ProfessionalOut)
def get_professional(professional_id: int, db: Session = Depends(get_db)):
    professional = (
        db.query(Professional)
        .options(joinedload(Professional.user), joinedload(Professional.category))
        .filter(Professional.id == professional_id)
        .first()
    )
    if not professional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")
    return build_professional_out(professional)


@router.post("", response_model=ProfessionalOut)
def create_professional(
    data: ProfessionalCreate,
    user: User = Depends(require_professional),
    db: Session = Depends(get_db),
):
    professional = Professional(user_id=user.id, **data.model_dump())
    db.add(professional)
    db.commit()
    db.refresh(professional)
    return build_professional_out(professional)


@router.put("/{professional_id}", response_model=ProfessionalOut)
def update_professional(
    professional_id: int,
    data: ProfessionalUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    professional = (
        db.query(Professional)
        .options(joinedload(Professional.user), joinedload(Professional.category))
        .filter(Professional.id == professional_id)
        .first()
    )
    if not professional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    if user.role != "admin" and professional.user_id != user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para editar este perfil")

    _apply_update(professional, data)
    db.commit()
    db.refresh(professional)
    return build_professional_out(professional)
