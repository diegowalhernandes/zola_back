from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.utils.text_normalize import (
    normalize_city,
    normalize_email,
    normalize_free_text,
    normalize_job_specs,
    normalize_name,
    normalize_professional_type,
    normalize_state,
)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserPublic"


class LoginInput(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_login_email(cls, value: str) -> str:
        return normalize_email(str(value))


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

    @field_validator("email", mode="before")
    @classmethod
    def normalize_user_email(cls, value: str) -> str:
        return normalize_email(str(value))

    @field_validator("name", mode="before")
    @classmethod
    def normalize_user_name(cls, value: str) -> str:
        return normalize_name(str(value))

    @field_validator("professional_type", mode="before")
    @classmethod
    def normalize_user_professional_type(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return normalize_professional_type(str(value))

    @field_validator("city", mode="before")
    @classmethod
    def normalize_user_city(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return value
        return normalize_city(str(value))

    @field_validator("title", "description", mode="before")
    @classmethod
    def normalize_user_profile_text(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return value
        return normalize_free_text(str(value))

    @field_validator("state", mode="before")
    @classmethod
    def normalize_user_state(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return value
        return normalize_state(str(value))

    @field_validator("job_specs", mode="before")
    @classmethod
    def normalize_user_job_specs(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return normalize_job_specs(value)


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

    @field_validator("title", "description", mode="before")
    @classmethod
    def normalize_profile_text(cls, value: str) -> str:
        return normalize_free_text(str(value))

    @field_validator("city", mode="before")
    @classmethod
    def normalize_profile_city(cls, value: str) -> str:
        return normalize_city(str(value))

    @field_validator("state", mode="before")
    @classmethod
    def normalize_profile_state(cls, value: str) -> str:
        return normalize_state(str(value))


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

    @field_validator("professional_type", mode="before")
    @classmethod
    def normalize_type(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return normalize_professional_type(str(value))

    @field_validator("title", "description", mode="before")
    @classmethod
    def normalize_profile_text(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return value
        return normalize_free_text(str(value))

    @field_validator("city", mode="before")
    @classmethod
    def normalize_profile_city(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return value
        return normalize_city(str(value))

    @field_validator("state", mode="before")
    @classmethod
    def normalize_profile_state(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return value
        return normalize_state(str(value))

    @field_validator("job_specs", mode="before")
    @classmethod
    def normalize_specs(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return normalize_job_specs(value)


class AppointmentCreate(BaseModel):
    professional_id: int
    appointment_date: date
    time_slot: str = Field(min_length=4, max_length=10)
    notes: str | None = None

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return value
        return normalize_free_text(str(value))


class AppointmentOut(BaseModel):
    id: int
    professional_id: int
    client_id: int
    appointment_date: date
    time_slot: str
    status: str
    notes: str | None = None
    total_amount: float = 0
    deposit_amount: float = 0
    deposit_paid: bool = False
    payment_status: str = "pending"
    created_at: datetime

    model_config = {"from_attributes": True}


class DepositPreviewOut(BaseModel):
    total_amount: float
    deposit_amount: float
    deposit_percent: float
    payments_enabled: bool
    slot_count: int = 1


class SlotSelection(BaseModel):
    appointment_date: date
    time_slot: str = Field(min_length=4, max_length=10)


class BatchCheckoutCreate(BaseModel):
    professional_id: int
    slots: list[SlotSelection] = Field(min_length=1, max_length=20)
    notes: str | None = None
    payment_mode: str = Field(default="deposit", pattern="^(deposit|full)$")

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return value
        return normalize_free_text(str(value))


class BatchCheckoutOut(BaseModel):
    batch_id: str
    appointment_ids: list[int]
    checkout_url: str | None = None
    total_amount: float
    amount_due: float
    deposit_amount: float
    payment_mode: str
    payments_required: bool
    status: str


class AppointmentCheckoutOut(BaseModel):
    appointment_id: int
    checkout_url: str | None = None
    deposit_amount: float
    total_amount: float
    payments_required: bool
    status: str


class AppointmentListItem(BaseModel):
    id: int
    professional_id: int
    client_id: int
    appointment_date: date
    time_slot: str
    status: str
    total_amount: float = 0
    deposit_amount: float = 0
    amount_due: float = 0
    deposit_paid: bool
    payment_status: str
    payment_mode: str | None = None
    batch_id: str | None = None
    notes: str | None = None
    professional_name: str | None = None
    client_name: str | None = None
    created_at: datetime


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

    @field_validator("client_name", mode="before")
    @classmethod
    def normalize_client_name(cls, value: str) -> str:
        return normalize_name(str(value))

    @field_validator("comment", mode="before")
    @classmethod
    def normalize_comment(cls, value: str) -> str:
        return normalize_free_text(str(value))


class RequestCreate(BaseModel):
    category_id: int
    professional_id: int | None = None
    title: str
    description: str
    location: str
    budget: float | None = None

    @field_validator("title", "description", "location", mode="before")
    @classmethod
    def normalize_request_text(cls, value: str) -> str:
        return normalize_free_text(str(value))


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

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        return normalize_free_text(str(value))


class MessageOut(BaseModel):
    id: int
    request_id: int
    sender_id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
