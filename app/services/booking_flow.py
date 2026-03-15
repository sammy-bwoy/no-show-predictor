from datetime import datetime, timedelta, timezone
import random
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    AppointmentLevelDetail,
    InternetActivityEvent,
    Patient,
    PatientBehaviorProfile,
    PatientNotificationEvent,
    PatientNotificationPreference,
    Provider,
)
from app.schemas import AppointmentConfirmRequest, AppointmentContext, BookingScheduleRequest, PatientSnapshot, ProviderSnapshot

PROVIDER_DIRECTORY = [
    {
        "provider_id": "prov-201",
        "full_name": "Dr. Maya Ellis",
        "specialty": "primary_care",
        "location_name": "Downtown Clinic",
        "location_address": "210 Hudson St, New York, NY 10013",
        "visit_instructions": "Bring insurance card and photo ID. Arrive 15 minutes early for check-in.",
        "latitude": 40.7128,
        "longitude": -74.0060,
    },
    {
        "provider_id": "prov-202",
        "full_name": "Dr. Noah Patel",
        "specialty": "cardiology",
        "location_name": "Riverside Health",
        "location_address": "480 Riverside Dr, New York, NY 10027",
        "visit_instructions": "Avoid caffeine for 4 hours before your visit unless instructed otherwise.",
        "latitude": 40.7399,
        "longitude": -73.9946,
    },
    {
        "provider_id": "prov-203",
        "full_name": "Dr. Ava Kim",
        "specialty": "dermatology",
        "location_name": "Midtown Medical",
        "location_address": "55 W 47th St, New York, NY 10036",
        "visit_instructions": "Please avoid heavy makeup or topical products on treatment area.",
        "latitude": 40.7549,
        "longitude": -73.9840,
    },
    {
        "provider_id": "prov-204",
        "full_name": "Dr. Lucas Green",
        "specialty": "orthopedics",
        "location_name": "Union Care Center",
        "location_address": "120 E 14th St, New York, NY 10003",
        "visit_instructions": "Bring prior scans/reports and wear comfortable clothing.",
        "latitude": 40.7359,
        "longitude": -73.9911,
    },
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


def _override_preferences_from_db(profile: dict, db: Session) -> dict:
    patient = db.query(Patient).filter(Patient.external_id == profile["patient_id"]).first()
    if patient is None:
        return profile

    pref = db.query(PatientNotificationPreference).filter(PatientNotificationPreference.patient_id == patient.id).first()
    if pref is None:
        return profile

    profile = {**profile}
    profile["messaging_preferences"] = {
        "allow_sms": pref.allow_sms,
        "allow_email": pref.allow_email,
        "allow_phone": pref.allow_phone,
        "allow_portal": pref.allow_portal,
        "preferred_channel": pref.preferred_channel,
    }
    return profile


def get_patient(patient_id: str, db: Session | None = None) -> dict | None:
    profile = PATIENT_BY_ID.get(patient_id)
    if profile is None:
        return None
    if db is None:
        return profile
    return _override_preferences_from_db(profile, db)


def update_patient_messaging_preferences(db: Session, patient_id: str, preferences: dict) -> dict | None:
    profile = PATIENT_BY_ID.get(patient_id)
    if profile is None:
        return None

    current = profile["messaging_preferences"]
    current["allow_sms"] = bool(preferences["allow_sms"])
    current["allow_email"] = bool(preferences["allow_email"])
    current["allow_phone"] = bool(preferences["allow_phone"])
    current["allow_portal"] = bool(preferences["allow_portal"])
    current["preferred_channel"] = preferences["preferred_channel"]

    patient = db.query(Patient).filter(Patient.external_id == patient_id).first()
    if patient is not None:
        pref = db.query(PatientNotificationPreference).filter(PatientNotificationPreference.patient_id == patient.id).first()
        if pref is None:
            pref = PatientNotificationPreference(patient_id=patient.id)
            db.add(pref)
        pref.allow_sms = current["allow_sms"]
        pref.allow_email = current["allow_email"]
        pref.allow_phone = current["allow_phone"]
        pref.allow_portal = current["allow_portal"]
        pref.preferred_channel = current["preferred_channel"]
        pref.updated_by = "practice_user"
        pref.updated_at = datetime.utcnow()
        db.commit()

    return profile


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


def _is_designated_new_patient(patient_id: str) -> bool:
    if patient_id == "pat-1005":
        return True
    try:
        n = int(patient_id.split("-")[-1])
        return n % 23 == 0
    except ValueError:
        return False


def _ensure_provider_row(db: Session, provider_profile: dict) -> Provider:
    provider = db.query(Provider).filter(Provider.external_id == provider_profile["provider_id"]).first()
    if provider is None:
        provider = Provider(
            external_id=provider_profile["provider_id"],
            specialty=provider_profile["specialty"],
            latitude=provider_profile["latitude"],
            longitude=provider_profile["longitude"],
        )
        db.add(provider)
        db.flush()
    return provider


def _ensure_patient_row(db: Session, patient_profile: dict) -> Patient:
    patient = db.query(Patient).filter(Patient.external_id == patient_profile["patient_id"]).first()
    if patient is None:
        patient = Patient(
            external_id=patient_profile["patient_id"],
            zip_code="10001" if patient_profile["country"] == "USA" else "400001",
        )
        db.add(patient)
        db.flush()
    return patient


def _seed_behavior_tables_if_needed(
    db: Session,
    patient: Patient,
    patient_profile: dict,
    primary_provider: Provider,
    scheduled_at: datetime,
) -> None:
    rng = random.Random(abs(hash(patient.external_id)) % (2**31))
    engagement = patient_profile["engagement"]

    behavior_profile = db.query(PatientBehaviorProfile).filter(PatientBehaviorProfile.patient_id == patient.id).first()
    if behavior_profile is None:
        behavior_profile = PatientBehaviorProfile(
            patient_id=patient.id,
            avg_weekly_web_sessions=round(engagement["email_rate"] * 10 + engagement["portal_rate"] * 8, 2),
            avg_weekly_portal_sessions=round(engagement["portal_rate"] * 12, 2),
            avg_daily_mobile_minutes=round(engagement["sms_rate"] * 18 + engagement["phone_rate"] * 8, 2),
            no_show_risk_behavior_score=round(max(0.05, 1 - (engagement["sms_rate"] + engagement["email_rate"]) / 2), 2),
        )
        db.add(behavior_profile)

    pref = db.query(PatientNotificationPreference).filter(PatientNotificationPreference.patient_id == patient.id).first()
    if pref is None:
        pref_src = patient_profile["messaging_preferences"]
        pref = PatientNotificationPreference(
            patient_id=patient.id,
            allow_sms=pref_src["allow_sms"],
            allow_email=pref_src["allow_email"],
            allow_phone=pref_src["allow_phone"],
            allow_portal=pref_src["allow_portal"],
            preferred_channel=pref_src["preferred_channel"],
            updated_by="bootstrap",
            updated_at=datetime.utcnow(),
        )
        db.add(pref)

    existing_activity = db.query(InternetActivityEvent).filter(InternetActivityEvent.patient_id == patient.id).count()
    if existing_activity == 0:
        for i in range(24):
            days_ago = rng.randint(3, 120)
            ev_time = datetime.utcnow() - timedelta(days=days_ago, hours=rng.randint(0, 23))
            activity_type = rng.choice(["portal_login", "portal_message", "education_view", "billing_view"]) 
            db.add(
                InternetActivityEvent(
                    patient_id=patient.id,
                    activity_type=activity_type,
                    channel="portal" if "portal" in activity_type else "web",
                    duration_seconds=rng.randint(30, 1200),
                    event_at=ev_time,
                    metadata_json={"source": "demo_seed"},
                )
            )

    prior_count = (
        db.query(Appointment)
        .filter(Appointment.patient_id == patient.id)
        .filter(Appointment.scheduled_at < scheduled_at)
        .count()
    )

    if prior_count == 0 and not _is_designated_new_patient(patient.external_id):
        n_history = rng.randint(6, 18)
        no_show_ratio = max(0.05, min(0.55, 1 - ((engagement["sms_rate"] + engagement["email_rate"] + engagement["portal_rate"]) / 3)))
        no_show_target = int(round(n_history * no_show_ratio))

        outcomes = [False] * no_show_target + [True] * (n_history - no_show_target)
        rng.shuffle(outcomes)

        channels = ["sms", "email", "phone", "portal"]
        for i, attended in enumerate(outcomes):
            hist_sched = scheduled_at - timedelta(days=rng.randint(15 + i * 20, 45 + i * 35))
            hist_sched = hist_sched.replace(hour=rng.choice([8, 9, 10, 11, 14, 15]), minute=0, second=0, microsecond=0)
            hist_booked = hist_sched - timedelta(days=rng.randint(2, 20))
            reminder_channel = channels[i % len(channels)]
            prior_no_show = sum(1 for x in outcomes[:i] if not x)

            appt = Appointment(
                external_id=f"hist2-{patient.external_id}-{i}",
                patient_id=patient.id,
                provider_id=primary_provider.id,
                appointment_type=rng.choice(["follow_up", "sick_visit", "annual_wellness"]),
                is_new_patient=(i == 0),
                is_telehealth=False,
                specialty=primary_provider.specialty,
                confirmation_channel=reminder_channel,
                weather_code=rng.choice(["clear", "cloudy", "rain"]),
                weather_temp_f=rng.uniform(58, 88),
                distance_miles=rng.uniform(0.8, 17.5),
                lead_time_hours=max((hist_sched - hist_booked).total_seconds() / 3600.0, 0.0),
                day_of_week=hist_sched.weekday(),
                hour_of_day=hist_sched.hour,
                prior_total_appts=i,
                prior_no_show_count=prior_no_show,
                prior_portal_logins_30d=rng.randint(0, 12),
                prior_reminder_response_rate=max(0.1, min(0.95, engagement["sms_rate"] - (prior_no_show / max(i, 1)) * 0.25 if i > 0 else engagement["sms_rate"])),
                digital_engagement_score=max(0.1, min(0.95, engagement["portal_rate"] + engagement["email_rate"] / 2)),
                provider_no_show_rate=0.12,
                status="completed" if attended else "no_show",
                label_attended=attended,
                booked_at=hist_booked,
                scheduled_at=hist_sched,
            )
            db.add(appt)
            db.flush()

            db.add(
                PatientNotificationEvent(
                    patient_id=patient.id,
                    appointment_id=appt.id,
                    channel=reminder_channel,
                    event_type="sent",
                    delivered=True,
                    responded=attended and rng.random() < 0.7,
                    sent_at=hist_booked + timedelta(hours=2),
                )
            )


def determine_best_reminder_channel(patient_profile: dict, db: Session) -> str:
    patient = db.query(Patient).filter(Patient.external_id == patient_profile["patient_id"]).first()
    db_pref = None
    if patient is not None:
        db_pref = db.query(PatientNotificationPreference).filter(PatientNotificationPreference.patient_id == patient.id).first()

    if db_pref is not None:
        prefs = {
            "allow_sms": db_pref.allow_sms,
            "allow_email": db_pref.allow_email,
            "allow_phone": db_pref.allow_phone,
            "allow_portal": db_pref.allow_portal,
            "preferred_channel": db_pref.preferred_channel,
        }
    else:
        prefs = patient_profile["messaging_preferences"]

    rates = patient_profile["engagement"]

    allowed = {
        "sms": prefs.get("allow_sms", True),
        "email": prefs.get("allow_email", True),
        "phone": prefs.get("allow_phone", True),
        "portal": prefs.get("allow_portal", True),
    }

    preferred = prefs.get("preferred_channel", "auto")
    if preferred in allowed and preferred != "auto" and allowed[preferred]:
        return preferred

    candidates = [
        ("sms", rates.get("sms_rate", 0.0)),
        ("email", rates.get("email_rate", 0.0)),
        ("phone", rates.get("phone_rate", 0.0)),
        ("portal", rates.get("portal_rate", 0.0)),
    ]
    candidates = [pair for pair in candidates if allowed.get(pair[0], False)]
    if not candidates:
        return "sms"
    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def _directions_url(address: str) -> str:
    query = address.replace(" ", "+")
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def build_confirmation_details(
    patient_profile: dict,
    provider_profile: dict,
    scheduled_at: datetime,
    appointment_type: str,
    duration_minutes: int,
    channel: str,
) -> dict:
    return {
        "patient_name": patient_profile["full_name"],
        "provider_name": provider_profile["full_name"],
        "location_name": provider_profile["location_name"],
        "location_address": provider_profile["location_address"],
        "appointment_type": appointment_type,
        "scheduled_at": scheduled_at,
        "duration_minutes": duration_minutes,
        "visit_instructions": provider_profile["visit_instructions"],
        "directions_url": _directions_url(provider_profile["location_address"]),
        "auto_notification_channel": channel,
    }


def save_appointment_level_details(db: Session, appointment_external_id: str, details: dict) -> None:
    appointment = db.query(Appointment).filter(Appointment.external_id == appointment_external_id).first()
    if appointment is None:
        return

    row = db.query(AppointmentLevelDetail).filter(AppointmentLevelDetail.appointment_id == appointment.id).first()
    if row is None:
        row = AppointmentLevelDetail(appointment_id=appointment.id)
        db.add(row)

    row.location_name = details["location_name"]
    row.location_address = details["location_address"]
    row.visit_instructions = details["visit_instructions"]
    row.directions_url = details["directions_url"]
    db.flush()


def build_background_confirm_request(db: Session, booking: BookingScheduleRequest) -> tuple[AppointmentConfirmRequest, dict, dict]:
    provider_profile = get_provider(booking.provider_id)
    patient_profile = get_patient(booking.patient_id, db=db)
    if patient_profile is None:
        raise ValueError(f"Unknown patient: {booking.patient_id}")
    if provider_profile is None:
        raise ValueError(f"Unknown provider: {booking.provider_id}")

    scheduled_at = booking.scheduled_at
    if scheduled_at.tzinfo is not None:
        scheduled_at = scheduled_at.astimezone(timezone.utc).replace(tzinfo=None)

    patient = _ensure_patient_row(db, patient_profile)
    provider = _ensure_provider_row(db, provider_profile)
    _seed_behavior_tables_if_needed(db, patient, patient_profile, provider, scheduled_at)

    prior_rows = (
        db.query(Appointment)
        .filter(Appointment.patient_id == patient.id)
        .filter(Appointment.scheduled_at < scheduled_at)
        .all()
    )

    prior_total = len(prior_rows)
    prior_no_show = len([row for row in prior_rows if row.status == "no_show" or row.label_attended is False])
    prior_no_show_rate = (prior_no_show / prior_total) if prior_total > 0 else 0.0

    provider_rows = (
        db.query(Appointment)
        .filter(Appointment.provider_id == provider.id)
        .filter(Appointment.label_attended.isnot(None))
        .all()
    )
    provider_no_show_rate = 0.12
    if provider_rows:
        provider_no_show_rate = len([row for row in provider_rows if row.label_attended is False]) / len(provider_rows)

    behavior = db.query(PatientBehaviorProfile).filter(PatientBehaviorProfile.patient_id == patient.id).first()
    if behavior is None:
        profile_engagement = patient_profile["engagement"]
        synthetic_portal_logins = max(0, min(12, prior_total // 2))
        synthetic_reminder_response = max(0.05, min(0.95, profile_engagement.get("sms_rate", 0.70) - (prior_no_show_rate * 0.35)))
        synthetic_digital_engagement = max(0.05, min(0.95, profile_engagement.get("portal_rate", 0.65) - (prior_no_show_rate * 0.30)))
    else:
        synthetic_portal_logins = int(round(min(20, behavior.avg_weekly_portal_sessions * 1.6)))
        synthetic_reminder_response = max(0.05, min(0.95, 0.85 - (behavior.no_show_risk_behavior_score * 0.55)))
        synthetic_digital_engagement = max(0.05, min(0.95, (behavior.avg_weekly_web_sessions / 12)))

    appointment_type = booking.appointment_type
    is_new_patient = appointment_type == "new_patient" or _is_designated_new_patient(patient.external_id) or prior_total == 0
    is_telehealth = appointment_type == "telehealth"
    default_distance = 0.0 if is_telehealth else 6.5

    booked_at = datetime.utcnow()
    appointment_external_id = f"appt-{uuid4().hex[:12]}"
    confirmation_channel = determine_best_reminder_channel(patient_profile, db)

    payload = AppointmentConfirmRequest(
        patient=PatientSnapshot(
            external_id=booking.patient_id,
            zip_code=patient.zip_code,
            latitude=patient.latitude,
            longitude=patient.longitude,
            prior_total_appts=prior_total,
            prior_no_show_count=prior_no_show,
            prior_portal_logins_30d=synthetic_portal_logins,
            prior_reminder_response_rate=synthetic_reminder_response,
            digital_engagement_score=synthetic_digital_engagement,
        ),
        provider=ProviderSnapshot(
            external_id=booking.provider_id,
            specialty=provider_profile["specialty"],
            latitude=provider.latitude,
            longitude=provider.longitude,
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

    confirmation = build_confirmation_details(
        patient_profile=patient_profile,
        provider_profile=provider_profile,
        scheduled_at=scheduled_at,
        appointment_type=appointment_type,
        duration_minutes=booking.duration_minutes,
        channel=confirmation_channel,
    )

    return payload, context, confirmation
