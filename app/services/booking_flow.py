from datetime import datetime, timedelta, timezone
import random
from uuid import uuid4

from sqlalchemy.orm import Session

from app.schemas import AppointmentConfirmRequest, AppointmentContext, BookingScheduleRequest, PatientSnapshot, ProviderSnapshot

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

US_FIRST_NAMES = [
    "Liam", "Olivia", "Noah", "Emma", "Ava", "Sophia", "Mason", "Lucas", "Amelia", "Ethan",
    "Charlotte", "Mia", "Logan", "Ella", "James", "Harper", "Benjamin", "Evelyn", "Henry", "Abigail",
]
US_LAST_NAMES = [
    "Smith", "Johnson", "Brown", "Davis", "Miller", "Wilson", "Taylor", "Anderson", "Thomas", "Moore",
    "Martin", "Jackson", "White", "Harris", "Clark", "Lewis", "Young", "Allen", "King", "Wright",
]
US_CITIES = [
    ("New York", "NY"), ("Chicago", "IL"), ("Houston", "TX"), ("Phoenix", "AZ"),
    ("Seattle", "WA"), ("Boston", "MA"), ("Miami", "FL"), ("Atlanta", "GA"),
]

IN_FIRST_NAMES = [
    "Aarav", "Vihaan", "Aditya", "Arjun", "Anaya", "Diya", "Saanvi", "Isha", "Rohan", "Sameer",
    "Priya", "Neha", "Aditi", "Kavya", "Rahul", "Karan", "Ishita", "Meera", "Lakshmi", "Anika",
]
IN_LAST_NAMES = [
    "Patel", "Sharma", "Verma", "Gupta", "Reddy", "Nair", "Iyer", "Mehta", "Yadav", "Singh",
    "Kumar", "Das", "Kapoor", "Mishra", "Bose", "Joshi", "Pillai", "Rao", "Chopra", "Agarwal",
]
IN_CITIES = [
    ("Mumbai", "MH"), ("Delhi", "DL"), ("Bengaluru", "KA"), ("Hyderabad", "TS"),
    ("Pune", "MH"), ("Ahmedabad", "GJ"), ("Chennai", "TN"), ("Kolkata", "WB"),
]

INSURANCE_PAYERS = ["Aetna", "Cigna", "BlueCross", "UnitedHealth", "Medicare", "Star Health", "ICICI Lombard"]
INSURANCE_PLANS = ["Basic", "Silver", "Gold Plus", "Family Care", "Premium", "Corporate Shield"]


def _default_messaging_preferences(preferred: str = "auto") -> dict:
    return {
        "allow_sms": True,
        "allow_email": True,
        "allow_phone": True,
        "allow_portal": True,
        "preferred_channel": preferred,
    }


def _build_seed_patients() -> list[dict]:
    return [
        {
            "patient_id": "pat-1001",
            "full_name": "Sameer Yadav",
            "date_of_birth": "1989-05-16",
            "sex": "male",
            "country": "USA",
            "city": "New York",
            "state": "NY",
            "phone": "(212) 555-0111",
            "email": "sameer.yadav@example.com",
            "address_line": "128 W 34th St",
            "insurance_payer": "Aetna",
            "insurance_plan": "Gold Plus",
            "member_id": "AET-1001",
            "default_provider_id": "prov-201",
            "engagement": {"sms_rate": 0.87, "email_rate": 0.50, "phone_rate": 0.35, "portal_rate": 0.28},
            "messaging_preferences": _default_messaging_preferences("sms"),
        },
        {
            "patient_id": "pat-1002",
            "full_name": "Amelia Carter",
            "date_of_birth": "1992-02-03",
            "sex": "female",
            "country": "USA",
            "city": "New York",
            "state": "NY",
            "phone": "(917) 555-0199",
            "email": "amelia.carter@example.com",
            "address_line": "52 Park Ave",
            "insurance_payer": "BlueCross",
            "insurance_plan": "Silver",
            "member_id": "BCBS-1002",
            "default_provider_id": "prov-202",
            "engagement": {"sms_rate": 0.64, "email_rate": 0.58, "phone_rate": 0.30, "portal_rate": 0.22},
            "messaging_preferences": _default_messaging_preferences("sms"),
        },
        {
            "patient_id": "pat-1003",
            "full_name": "Rohan Mehta",
            "date_of_birth": "1984-11-27",
            "sex": "male",
            "country": "India",
            "city": "Mumbai",
            "state": "MH",
            "phone": "+91-98765-10103",
            "email": "rohan.mehta@example.in",
            "address_line": "18 Bandra West",
            "insurance_payer": "Star Health",
            "insurance_plan": "Premium",
            "member_id": "STAR-1003",
            "default_provider_id": "prov-203",
            "engagement": {"sms_rate": 0.79, "email_rate": 0.36, "phone_rate": 0.48, "portal_rate": 0.18},
            "messaging_preferences": _default_messaging_preferences("sms"),
        },
        {
            "patient_id": "pat-1004",
            "full_name": "Lina Rodriguez",
            "date_of_birth": "1976-09-10",
            "sex": "female",
            "country": "USA",
            "city": "New York",
            "state": "NY",
            "phone": "(718) 555-0144",
            "email": "lina.rodriguez@example.com",
            "address_line": "204 5th Ave",
            "insurance_payer": "UnitedHealth",
            "insurance_plan": "Family Care",
            "member_id": "UHC-1004",
            "default_provider_id": "prov-201",
            "engagement": {"sms_rate": 0.41, "email_rate": 0.22, "phone_rate": 0.67, "portal_rate": 0.12},
            "messaging_preferences": _default_messaging_preferences("phone"),
        },
        {
            "patient_id": "pat-1005",
            "full_name": "Kevin Johnson",
            "date_of_birth": "1999-04-21",
            "sex": "male",
            "country": "USA",
            "city": "New York",
            "state": "NY",
            "phone": "(646) 555-0142",
            "email": "kevin.johnson@example.com",
            "address_line": "322 Broadway",
            "insurance_payer": "Cigna",
            "insurance_plan": "Basic",
            "member_id": "CIG-1005",
            "default_provider_id": None,
            "engagement": {"sms_rate": 0.30, "email_rate": 0.44, "phone_rate": 0.20, "portal_rate": 0.26},
            "messaging_preferences": _default_messaging_preferences("auto"),
        },
    ]


def _build_large_demo_patients(n_more: int = 50_000) -> list[dict]:
    rng = random.Random(20260315)
    rows = []
    for idx in range(n_more):
        is_india = idx % 2 == 1
        if is_india:
            first = rng.choice(IN_FIRST_NAMES)
            last = rng.choice(IN_LAST_NAMES)
            city, state = rng.choice(IN_CITIES)
            country = "India"
            phone = f"+91-9{rng.randint(1000, 9999)}-{rng.randint(10000, 99999)}"
            email = f"{first.lower()}.{last.lower()}{idx}@example.in"
        else:
            first = rng.choice(US_FIRST_NAMES)
            last = rng.choice(US_LAST_NAMES)
            city, state = rng.choice(US_CITIES)
            country = "USA"
            phone = f"({rng.randint(200, 989)}) 555-{rng.randint(1000, 9999)}"
            email = f"{first.lower()}.{last.lower()}{idx}@example.com"

        year = rng.randint(1952, 2007)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        sex = rng.choice(["male", "female"])
        patient_num = 200000 + idx
        preferred = rng.choice(["auto", "sms", "email", "phone", "portal"])

        rows.append(
            {
                "patient_id": f"pat-{patient_num}",
                "full_name": f"{first} {last}",
                "date_of_birth": f"{year:04d}-{month:02d}-{day:02d}",
                "sex": sex,
                "country": country,
                "city": city,
                "state": state,
                "phone": phone,
                "email": email,
                "address_line": f"{rng.randint(1, 999)} Main Street",
                "insurance_payer": rng.choice(INSURANCE_PAYERS),
                "insurance_plan": rng.choice(INSURANCE_PLANS),
                "member_id": f"M-{patient_num}",
                "default_provider_id": rng.choice(["prov-201", "prov-202", "prov-203", "prov-204", None]),
                "engagement": {
                    "sms_rate": round(rng.uniform(0.20, 0.95), 2),
                    "email_rate": round(rng.uniform(0.15, 0.85), 2),
                    "phone_rate": round(rng.uniform(0.10, 0.75), 2),
                    "portal_rate": round(rng.uniform(0.10, 0.90), 2),
                },
                "messaging_preferences": _default_messaging_preferences(preferred),
            }
        )

    return rows


PATIENT_DIRECTORY = _build_seed_patients() + _build_large_demo_patients()
PATIENT_BY_ID = {p["patient_id"]: p for p in PATIENT_DIRECTORY}


def search_patients(query: str, limit: int = 40) -> list[dict]:
    term = query.strip().lower()
    if not term:
        return []

    matches = [
        p
        for p in PATIENT_DIRECTORY
        if term in p["patient_id"].lower() or term in p["full_name"].lower() or term in p["phone"].lower()
    ]
    return matches[:limit]


def get_patient(patient_id: str) -> dict | None:
    return PATIENT_BY_ID.get(patient_id)


def update_patient_messaging_preferences(patient_id: str, preferences: dict) -> dict | None:
    patient = get_patient(patient_id)
    if patient is None:
        return None

    current = patient["messaging_preferences"]
    current["allow_sms"] = bool(preferences["allow_sms"])
    current["allow_email"] = bool(preferences["allow_email"])
    current["allow_phone"] = bool(preferences["allow_phone"])
    current["allow_portal"] = bool(preferences["allow_portal"])
    current["preferred_channel"] = preferences["preferred_channel"]
    return patient


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


def _business_start(dt: datetime | None) -> datetime:
    start = (dt or datetime.utcnow()).replace(hour=0, minute=0, second=0, microsecond=0)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    return start


def provider_week_availability(db: Session, provider_external_id: str, week_start: datetime | None = None) -> list[dict]:
    start = _business_start(week_start)

    business_days: list[datetime] = []
    cursor = start
    while len(business_days) < 5:
        if cursor.weekday() < 5:
            business_days.append(cursor)
        cursor += timedelta(days=1)

    end = business_days[-1] + timedelta(days=1)

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
    for day_dt in business_days:
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


def determine_best_reminder_channel(patient_profile: dict | None) -> str:
    if patient_profile is None:
        return "sms"

    prefs = patient_profile["messaging_preferences"]
    rates = patient_profile["engagement"]

    allowed = {
        "sms": prefs.get("allow_sms", True),
        "email": prefs.get("allow_email", True),
        "phone": prefs.get("allow_phone", True),
        "portal": prefs.get("allow_portal", True),
    }

    preferred = prefs.get("preferred_channel", "auto")
    if preferred in allowed and allowed[preferred]:
        return preferred

    candidates = [("sms", rates.get("sms_rate", 0.0)), ("email", rates.get("email_rate", 0.0)), ("phone", rates.get("phone_rate", 0.0)), ("portal", rates.get("portal_rate", 0.0))]
    candidates = [pair for pair in candidates if allowed.get(pair[0], False)]
    if not candidates:
        return "sms"
    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def build_background_confirm_request(db: Session, booking: BookingScheduleRequest) -> tuple[AppointmentConfirmRequest, dict]:
    from app.models import Appointment, Patient, Provider

    provider_profile = get_provider(booking.provider_id)
    patient_profile = get_patient(booking.patient_id)

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

    profile_engagement = patient_profile["engagement"] if patient_profile else {}
    synthetic_portal_logins = max(0, min(12, prior_total // 2))
    synthetic_reminder_response = max(0.05, min(0.95, profile_engagement.get("sms_rate", 0.70) - (prior_no_show_rate * 0.35)))
    synthetic_digital_engagement = max(0.05, min(0.95, profile_engagement.get("portal_rate", 0.65) - (prior_no_show_rate * 0.30)))

    appointment_type = booking.appointment_type
    is_new_patient = appointment_type == "new_patient" or prior_total == 0
    is_telehealth = appointment_type == "telehealth"
    default_distance = 0.0 if is_telehealth else 6.5

    booked_at = datetime.utcnow()
    appointment_external_id = f"appt-{uuid4().hex[:12]}"
    confirmation_channel = determine_best_reminder_channel(patient_profile)

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
            confirmation_channel=confirmation_channel,
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
        "reminder_channel": confirmation_channel,
        "notes": booking.notes,
        "duration_minutes": booking.duration_minutes,
    }

    return payload, context
