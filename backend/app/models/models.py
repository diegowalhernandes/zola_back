from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="client")  # client | professional | admin
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    professional_profile = relationship("Professional", back_populates="user", uselist=False)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(80), default="FaTools")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    professionals = relationship("Professional", back_populates="category")


class Professional(Base):
    __tablename__ = "professionals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    price_from: Mapped[float] = mapped_column(Float, default=0)
    rating: Mapped[float] = mapped_column(Float, default=5)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    whatsapp: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    professional_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # diarista | baba
    job_specs: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    availability: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON semanal

    user = relationship("User", back_populates="professional_profile")
    category = relationship("Category", back_populates="professionals")
    reviews = relationship("Review", back_populates="professional")
    appointments = relationship("Appointment", back_populates="professional")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    time_slot: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="awaiting_payment")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    deposit_amount: Mapped[float] = mapped_column(Float, default=0)
    deposit_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    payment_status: Mapped[str] = mapped_column(String(30), default="pending")
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payment_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amount_due: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    professional = relationship("Professional", back_populates="appointments")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), nullable=False)
    client_name: Mapped[str] = mapped_column(String(120), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    professional = relationship("Professional", back_populates="reviews")


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    professional_id: Mapped[int | None] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"), nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
