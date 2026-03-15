from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    zip_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    specialty: Mapped[str] = mapped_column(String(64), default="general")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="provider")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), index=True)

    appointment_type: Mapped[str] = mapped_column(String(64), default="follow_up")
    is_new_patient: Mapped[bool] = mapped_column(Boolean, default=False)
    is_telehealth: Mapped[bool] = mapped_column(Boolean, default=False)
    specialty: Mapped[str] = mapped_column(String(64), default="general")
    confirmation_channel: Mapped[str] = mapped_column(String(32), default="sms")
    weather_code: Mapped[str] = mapped_column(String(32), default="clear")
    weather_temp_f: Mapped[float] = mapped_column(Float, default=72.0)

    distance_miles: Mapped[float] = mapped_column(Float, default=5.0)
    lead_time_hours: Mapped[float] = mapped_column(Float, default=24.0)
    day_of_week: Mapped[int] = mapped_column(Integer, default=0)
    hour_of_day: Mapped[int] = mapped_column(Integer, default=9)

    prior_total_appts: Mapped[int] = mapped_column(Integer, default=0)
    prior_no_show_count: Mapped[int] = mapped_column(Integer, default=0)
    prior_portal_logins_30d: Mapped[int] = mapped_column(Integer, default=0)
    prior_reminder_response_rate: Mapped[float] = mapped_column(Float, default=0.0)
    digital_engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    provider_no_show_rate: Mapped[float] = mapped_column(Float, default=0.10)

    status: Mapped[str] = mapped_column(String(32), default="confirmed")
    label_attended: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    booking_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    booked_at: Mapped[datetime] = mapped_column(DateTime)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped[Patient] = relationship(back_populates="appointments")
    provider: Mapped[Provider] = relationship(back_populates="appointments")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="appointment")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), index=True)

    attendance_probability: Mapped[float] = mapped_column(Float)
    no_show_probability: Mapped[float] = mapped_column(Float)
    risk_band: Mapped[str] = mapped_column(String(16))
    confidence_score: Mapped[float] = mapped_column(Float, default=0.50)
    insufficient_data: Mapped[bool] = mapped_column(Boolean, default=False)

    recommended_actions: Mapped[list[str]] = mapped_column(JSON)
    reason_codes: Mapped[list[str]] = mapped_column(JSON)

    model_version: Mapped[str] = mapped_column(String(64), default="heuristic-v1")
    trigger_source: Mapped[str] = mapped_column(String(32), default="booking_confirmation")
    predicted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    appointment: Mapped[Appointment] = relationship(back_populates="predictions")
    feedback_items: Mapped[list["PredictionFeedback"]] = relationship(back_populates="prediction")


class PredictionFeedback(Base):
    __tablename__ = "prediction_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id"), index=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), index=True)

    is_wrong: Mapped[bool] = mapped_column(Boolean)
    reason_text: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    submitted_by: Mapped[str] = mapped_column(String(128), default="scheduler")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    prediction: Mapped[Prediction] = relationship(back_populates="feedback_items")
