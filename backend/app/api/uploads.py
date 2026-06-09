from fastapi import APIRouter, File, UploadFile

from app.services.storage_service import store_uploaded_image

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("/image")
def upload_image(file: UploadFile = File(...)):
    return store_uploaded_image(file)
