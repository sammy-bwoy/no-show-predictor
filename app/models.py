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
    behavior_profile: Mapped["PatientBehaviorProfile | None"] = relationship(back_populates="patient")
    internet_activity_events: Mapped[list["InternetActivityEvent"]] = relationship(back_populates="patient")
    notification_preference: Mapped["PatientNotificationPreference | None"] = relationship(back_populates="patient")
    notification_events: Mapped[list["PatientNotificationEvent"]] = relationship(back_populates="patient")


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
    appointment_detail: Mapped["AppointmentLevelDetail | None"] = relationship(back_populates="appointment")


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


class PatientBehaviorProfile(Base):
    __tablename__ = "patient_behavior_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), unique=True, index=True)
    avg_weekly_web_sessions: Mapped[float] = mapped_column(Float, default=2.0)
    avg_weekly_portal_sessions: Mapped[float] = mapped_column(Float, default=1.0)
    avg_daily_mobile_minutes: Mapped[float] = mapped_column(Float, default=10.0)
    no_show_risk_behavior_score: Mapped[float] = mapped_column(Float, default=0.40)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped[Patient] = relationship(back_populates="behavior_profile")


class InternetActivityEvent(Base):
    __tablename__ = "internet_activity_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    activity_type: Mapped[str] = mapped_column(String(64), default="portal_login")
    channel: Mapped[str] = mapped_column(String(32), default="portal")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    event_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    patient: Mapped[Patient] = relationship(back_populates="internet_activity_events")


class PatientNotificationPreference(Base):
    __tablename__ = "patient_notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), unique=True, index=True)
    allow_sms: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_email: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_phone: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_portal: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_channel: Mapped[str] = mapped_column(String(32), default="auto")
    updated_by: Mapped[str] = mapped_column(String(64), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped[Patient] = relationship(back_populates="notification_preference")


class PatientNotificationEvent(Base):
    __tablename__ = "patient_notification_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(32), default="sms")
    event_type: Mapped[str] = mapped_column(String(32), default="sent")
    delivered: Mapped[bool] = mapped_column(Boolean, default=True)
    responded: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped[Patient] = relationship(back_populates="notification_events")


class AppointmentLevelDetail(Base):
    __tablename__ = "appointment_level_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), unique=True, index=True)
    location_name: Mapped[str] = mapped_column(String(128), default="Clinic")
    location_address: Mapped[str] = mapped_column(String(255), default="")
    visit_instructions: Mapped[str] = mapped_column(String(1000), default="")
    directions_url: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    appointment: Mapped[Appointment] = relationship(back_populates="appointment_detail")
