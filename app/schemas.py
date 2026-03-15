from datetime import datetime

from pydantic import BaseModel, Field


class PatientSnapshot(BaseModel):
    external_id: str
    zip_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    prior_total_appts: int = Field(default=0, ge=0)
    prior_no_show_count: int = Field(default=0, ge=0)
    prior_portal_logins_30d: int = Field(default=0, ge=0)
    prior_reminder_response_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    digital_engagement_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ProviderSnapshot(BaseModel):
    external_id: str
    specialty: str = "general"
    latitude: float | None = None
    longitude: float | None = None
    provider_no_show_rate: float = Field(default=0.10, ge=0.0, le=1.0)


class AppointmentContext(BaseModel):
    external_id: str
    appointment_type: str = "follow_up"
    is_new_patient: bool = False
    is_telehealth: bool = False

    booked_at: datetime
    scheduled_at: datetime

    confirmation_channel: str = "sms"
    weather_code: str = "clear"
    weather_temp_f: float = 72.0
    distance_miles: float | None = Field(default=None, ge=0.0)


class AppointmentConfirmRequest(BaseModel):
    patient: PatientSnapshot
    provider: ProviderSnapshot
    appointment: AppointmentContext
    trigger_source: str = "booking_confirmation"


class AppointmentPredictionResponse(BaseModel):
    prediction_id: int
    appointment_id: int

    attendance_likelihood_pct: float | None = None
    no_show_likelihood_pct: float | None = None
    risk_band: str
    risk_label: str
    confidence_score: float
    confidence_label: str
    show_numeric_score: bool

    recommended_actions: list[str]
    reason_codes: list[str]
    model_version: str


class PatientSearchResult(BaseModel):
    patient_id: str
    full_name: str
    date_of_birth: str
    phone: str
    default_provider_id: str | None = None


class ProviderSearchResult(BaseModel):
    provider_id: str
    full_name: str
    specialty: str
    location_name: str


class ProviderSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    available: bool


class ProviderDayAvailability(BaseModel):
    day: str
    slots: list[ProviderSlot]


class BookingScheduleRequest(BaseModel):
    patient_id: str
    provider_id: str
    scheduled_at: datetime
    appointment_type: str
    duration_minutes: int = Field(ge=15, le=180)
    urgent_care: bool = False
    insurance_payer: str | None = None
    insurance_plan: str | None = None
    member_id: str | None = None
    referral_required: bool = False
    referral_id: str | None = None
    reason_for_visit: str | None = None
    interpreter_needed: bool = False
    reminder_channel: str = "sms"
    contact_name: str | None = None
    contact_phone: str | None = None
    notes: str | None = None


class BookingScheduleResponse(BaseModel):
    appointment_external_id: str
    prediction: AppointmentPredictionResponse


class FeedbackRequest(BaseModel):
    is_wrong: bool
    reason_text: str | None = Field(default=None, max_length=1000)
    submitted_by: str = "scheduler"


class OutcomeLabelRequest(BaseModel):
    attended: bool
