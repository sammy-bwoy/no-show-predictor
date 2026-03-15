from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.schemas import AppointmentConfirmRequest, AppointmentContext, BookingScheduleRequest, PatientSnapshot, ProviderSnapshot

PATIENT_DIRECTORY = [
    {"patient_id": "pat-1001", "full_name": "Sameer Yadav",    "date_of_birth": "1989-05-16", "phone": "(212) 555-0111", "default_provider_id": "prov-201"},
    {"patient_id": "pat-1002", "full_name": "Amelia Carter",   "date_of_birth": "1992-02-03", "phone": "(917) 555-0199", "default_provider_id": "prov-202"},
    {"patient_id": "pat-1003", "full_name": "Rohan Mehta",     "date_of_birth": "1984-11-27", "phone": "(332) 555-0181", "default_provider_id": "prov-203"},
    {"patient_id": "pat-1004", "full_name": "Lina Rodriguez",  "date_of_birth": "1976-09-10", "phone": "(718) 555-0144", "default_provider_id": "prov-201"},
    {"patient_id": "pat-1005", "full_name": "Kevin Johnson",   "date_of_birth": "1999-04-21", "phone": "(646) 555-0142", "default_provider_id": None},
]

PROVIDER_DIRECTORY = [
    {"provider_id": "prov-201", "full_name": "Dr. Maya Ellis", "specialty": "primary_care", "location_name": "Downtown Clinic", "latitude": 40.7128, "longitude": -74.0060},
    {"provider_id": "prov-202", "full_name": "Dr. Noah Patel", "specialty": "cardiology", "location_name": "Riverside Health", "latitude": 40.7399, "longitude": -73.9946},
    {"provider_id": "prov-203", "full_name": "Dr. Ava Kim", "specialty": "dermatology", "location_name": "Midtown Medical", "latitude": 40.7549, "longitude": -73.9840},
    {"provider_id": "prov-204", "full_name": "Dr. Lucas Green", "specialty": "orthopedics", "location_name": "Union Care Center", "latitude": 40.7359, "longitude": -73.9911},
]

APPOINTMENT_TYPE_DEFAULT_DURATION = {
    "new_patient": 45,
    "follow_up": 20,
    "telehealth": 20,
    "procedure": 60,
    "sick_visit": 15,
    "annual_wellness": 30,
    "urgent_care": 20,
}


def search_patients(query: str) -> list[dict]:
    term = query.strip().lower()
    if not term:
        return PATIENT_DIRECTORY
    return [
        p
        for p in PATIENT_DIRECTORY
        if term in p["patient_id"].lower() or term in p["full_name"].lower()
    ]


def search_providers(query: str) -> list[dict]:
    term = query.strip().lower()
    if not term:
        return PROVIDER_DIRECTORY
    return [
        p
        for p in PROVIDER_DIRECTORY
        if term in p["provider_id"].lower() or term in p["full_name"].lower() or term in p["specialty"].lower()
    ]


def get_provider(provider_id: str) -> dict | None:
    for provider in PROVIDER_DIRECTORY:
        if provider["provider_id"] == provider_id:
            return provider
    return None


def _week_start(dt: datetime | None) -> datetime:
    now = dt or datetime.utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def provider_week_availability(db: Session, provider_external_id: str, week_start: datetime | None = None) -> list[dict]:
    start = _week_start(week_start)
    end = start + timedelta(days=7)

    from app.models import Appointment, Provider

    provider = db.query(Provider).filter(Provider.external_id == provider_external_id).first()
    busy_keys: set[str] = set()
    if provider is not None:
        scheduled = (
            db.query(Appointment)
            .filter(Appointment.provider_id == provider.id)
            .filter(Appointment.scheduled_at >= start)
            .filter(Appointment.scheduled_at < end)
            .all()
        )
        for appt in scheduled:
            busy_keys.add(appt.scheduled_at.replace(minute=(appt.scheduled_at.minute // 30) * 30, second=0, microsecond=0).isoformat())

    days = []
    for day_index in range(7):
        day_dt = start + timedelta(days=day_index)
        slots = []
        for hour in range(8, 17):
            for minute in (0, 30):
                slot_start = day_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
                slot_end = slot_start + timedelta(minutes=30)
                key = slot_start.isoformat()
                slots.append(
                    {
                        "start_time": slot_start,
                        "end_time": slot_end,
                        "available": key not in busy_keys and slot_start > datetime.utcnow(),
                    }
                )
        days.append({"day": day_dt.strftime("%A %b %d"), "slots": slots})

    return days


def build_background_confirm_request(db: Session, booking: BookingScheduleRequest) -> tuple[AppointmentConfirmRequest, dict]:
    from app.models import Appointment, Patient, Provider

    provider_profile = get_provider(booking.provider_id)

    patient = db.query(Patient).filter(Patient.external_id == booking.patient_id).first()
    provider = db.query(Provider).filter(Provider.external_id == booking.provider_id).first()

    scheduled_at = booking.scheduled_at
    if scheduled_at.tzinfo is not None:
        scheduled_at = scheduled_at.astimezone(timezone.utc).replace(tzinfo=None)

    prior_rows = []
    if patient is not None:
        prior_rows = (
            db.query(Appointment)
            .filter(Appointment.patient_id == patient.id)
            .filter(Appointment.scheduled_at < scheduled_at)
            .all()
        )

    prior_total = len(prior_rows)
    prior_no_show = len([row for row in prior_rows if row.status == "no_show" or row.label_attended is False])
    prior_no_show_rate = (prior_no_show / prior_total) if prior_total > 0 else 0.0

    provider_rows = []
    if provider is not None:
        provider_rows = (
            db.query(Appointment)
            .filter(Appointment.provider_id == provider.id)
            .filter(Appointment.label_attended.isnot(None))
            .all()
        )

    provider_no_show_rate = 0.12
    if provider_rows:
        provider_no_show_rate = len([row for row in provider_rows if row.label_attended is False]) / len(provider_rows)

    synthetic_portal_logins = max(0, min(12, prior_total // 2))
    synthetic_reminder_response = max(0.05, min(0.95, 0.70 - (prior_no_show_rate * 0.5)))
    synthetic_digital_engagement = max(0.05, min(0.95, 0.72 - (prior_no_show_rate * 0.45)))

    appointment_type = booking.appointment_type
    is_new_patient = appointment_type == "new_patient" or prior_total == 0
    is_telehealth = appointment_type == "telehealth"
    default_distance = 0.0 if is_telehealth else 6.5

    booked_at = datetime.utcnow()
    appointment_external_id = f"appt-{uuid4().hex[:12]}"

    payload = AppointmentConfirmRequest(
        patient=PatientSnapshot(
            external_id=booking.patient_id,
            zip_code=patient.zip_code if patient else None,
            latitude=patient.latitude if patient else None,
            longitude=patient.longitude if patient else None,
            prior_total_appts=prior_total,
            prior_no_show_count=prior_no_show,
            prior_portal_logins_30d=synthetic_portal_logins,
            prior_reminder_response_rate=synthetic_reminder_response,
            digital_engagement_score=synthetic_digital_engagement,
        ),
        provider=ProviderSnapshot(
            external_id=booking.provider_id,
            specialty=provider_profile["specialty"] if provider_profile else "general",
            latitude=provider.latitude if provider else (provider_profile["latitude"] if provider_profile else None),
            longitude=provider.longitude if provider else (provider_profile["longitude"] if provider_profile else None),
            provider_no_show_rate=provider_no_show_rate,
        ),
        appointment=AppointmentContext(
            external_id=appointment_external_id,
            appointment_type=appointment_type,
            is_new_patient=is_new_patient,
            is_telehealth=is_telehealth,
            booked_at=booked_at,
            scheduled_at=scheduled_at,
            confirmation_channel=booking.reminder_channel,
            weather_code="clear",
            weather_temp_f=72.0,
            distance_miles=default_distance,
        ),
        trigger_source="booking_confirmation",
    )

    context = {
        "urgent_care": booking.urgent_care,
        "insurance_payer": booking.insurance_payer,
        "insurance_plan": booking.insurance_plan,
        "member_id": booking.member_id,
        "referral_required": booking.referral_required,
        "referral_id": booking.referral_id,
        "reason_for_visit": booking.reason_for_visit,
        "interpreter_needed": booking.interpreter_needed,
        "contact_name": booking.contact_name,
        "contact_phone": booking.contact_phone,
        "reminder_channel": booking.reminder_channel,
        "notes": booking.notes,
        "duration_minutes": booking.duration_minutes,
    }

    return payload, context
