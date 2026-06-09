from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import HTTPException, UploadFile

from app.core.config import settings

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def _safe_extension(filename: str | None) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ext
    return ".jpg"


def _upload_local(filename: str, content: bytes) -> str:
    file_path = UPLOAD_DIR / filename
    file_path.write_bytes(content)
    base_url = settings.public_api_base_url.rstrip("/")
    return f"{base_url}/media/{filename}"


def _upload_supabase(filename: str, content: bytes, content_type: str) -> str:
    bucket = settings.SUPABASE_STORAGE_BUCKET.strip("/")
    base = settings.SUPABASE_URL.rstrip("/")
    object_path = f"{bucket}/{filename}"
    upload_url = f"{base}/storage/v1/object/{object_path}"

    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    try:
        response = httpx.post(upload_url, content=content, headers=headers, timeout=30.0)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Falha ao enviar imagem para o storage.") from exc

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Storage rejeitou o upload ({response.status_code}). Verifique bucket e permissões no Supabase.",
        )

    return f"{base}/storage/v1/object/public/{object_path}"


def store_uploaded_image(file: UploadFile) -> dict[str, str]:
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Imagem muito grande (máx. 5 MB).")

    filename = f"{uuid4()}{_safe_extension(file.filename)}"
    content_type = file.content_type or "application/octet-stream"

    if settings.supabase_storage_configured:
        url = _upload_supabase(filename, content, content_type)
    else:
        url = _upload_local(filename, content)

    return {"filename": filename, "url": url}
