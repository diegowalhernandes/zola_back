from app.models.models import Professional
from app.schemas.schemas import ProfessionalOut, UserPublic
from app.utils.json_fields import loads_json
from app.utils.media_url import sanitize_media_url


def build_professional_out(professional: Professional) -> ProfessionalOut:
    user = professional.user
    safe_user = None
    if user:
        safe_user = UserPublic(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            avatar=sanitize_media_url(user.avatar),
        )

    return ProfessionalOut(
        id=professional.id,
        user_id=professional.user_id,
        category_id=professional.category_id,
        title=professional.title,
        description=professional.description,
        city=professional.city,
        state=professional.state,
        price_from=professional.price_from,
        rating=professional.rating,
        reviews_count=professional.reviews_count,
        whatsapp=professional.whatsapp,
        is_featured=professional.is_featured,
        image=sanitize_media_url(professional.image),
        latitude=professional.latitude,
        longitude=professional.longitude,
        professional_type=professional.professional_type,
        job_specs=loads_json(professional.job_specs),
        availability=loads_json(professional.availability),
        user=safe_user or professional.user,
        category=professional.category,
    )
