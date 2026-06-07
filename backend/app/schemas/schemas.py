from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserPublic"


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6)
    role: str = Field(pattern="^(client|professional)$", default="client")
    professional_type: str | None = Field(default=None, pattern="^(diarista|baba)$")
    category_id: int | None = None
    city: str | None = None
    state: str | None = Field(default=None, min_length=2, max_length=2)
    title: str | None = None
    description: str | None = None
    price_from: float | None = None
    job_specs: dict[str, Any] | None = None


class UserPublic(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    avatar: str | None = None

    model_config = {"from_attributes": True}


class CategoryOut(BaseModel):
    id: int
    name: str
    icon: str
    description: str | None = None

    model_config = {"from_attributes": True}


class ProfessionalOut(BaseModel):
    id: int
    user_id: int
    category_id: int
    title: str
    description: str
    city: str
    state: str
    price_from: float
    rating: float
    reviews_count: int
    whatsapp: str | None = None
    is_featured: bool
    image: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    professional_type: str | None = None
    job_specs: dict[str, Any] | None = None
    availability: dict[str, list[str]] | None = None
    user: UserPublic
    category: CategoryOut

    model_config = {"from_attributes": True}


class ProfessionalCreate(BaseModel):
    category_id: int
    title: str
    description: str
    city: str
    state: str = Field(min_length=2, max_length=2)
    price_from: float = 0
    whatsapp: str | None = None
    image: str | None = None


class ProfessionalUpdate(BaseModel):
    category_id: int | None = None
    title: str | None = None
    description: str | None = None
    city: str | None = None
    state: str | None = Field(default=None, min_length=2, max_length=2)
    price_from: float | None = None
    whatsapp: str | None = None
    image: str | None = None
    professional_type: str | None = Field(default=None, pattern="^(diarista|baba)$")
    job_specs: dict[str, Any] | None = None
    availability: dict[str, list[str]] | None = None


class AppointmentCreate(BaseModel):
    professional_id: int
    appointment_date: date
    time_slot: str = Field(min_length=4, max_length=10)
    notes: str | None = None


class AppointmentOut(BaseModel):
    id: int
    professional_id: int
    client_id: int
    appointment_date: date
    time_slot: str
    status: str
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DayAvailability(BaseModel):
    date: date
    slots: list[str]


class ReviewOut(BaseModel):
    id: int
    professional_id: int
    client_name: str
    rating: int
    comment: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    professional_id: int
    client_name: str
    rating: int = Field(ge=1, le=5)
    comment: str


class RequestCreate(BaseModel):
    category_id: int
    professional_id: int | None = None
    title: str
    description: str
    location: str
    budget: float | None = None


class RequestOut(BaseModel):
    id: int
    client_id: int
    professional_id: int | None = None
    category_id: int
    title: str
    description: str
    location: str
    status: str
    budget: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    request_id: int
    content: str


class MessageOut(BaseModel):
    id: int
    request_id: int
    sender_id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
