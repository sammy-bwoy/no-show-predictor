from datetime import datetime, timedelta
import random

from sqlalchemy.orm import Session

from app.models import Appointment, Patient, Provider


def seed_known_patients(db: Session) -> None:
    """
    Ensure the five booking-journey demo patients have realistic historical
    appointment records so the no-show model can score them properly.
    pat-1005 (Kevin Johnson) is intentionally left with zero history — new patient.
    Safe to call on every startup; individual sections are idempotent.
    """
    _rng = random.Random(77)

    dir_providers = [
        {"external_id": "prov-201", "specialty": "primary_care", "latitude": 40.7128, "longitude": -74.0060},
        {"external_id": "prov-202", "specialty": "cardiology", "latitude": 40.7399, "longitude": -73.9946},
        {"external_id": "prov-203", "specialty": "dermatology", "latitude": 40.7549, "longitude": -73.9840},
        {"external_id": "prov-204", "specialty": "orthopedics", "latitude": 40.7359, "longitude": -73.9911},
    ]
    prov_map: dict[str, Provider] = {}
    for pd in dir_providers:
        p = db.query(Provider).filter(Provider.external_id == pd["external_id"]).first()
        if p is None:
            p = Provider(**pd)
            db.add(p)
            db.flush()
        prov_map[pd["external_id"]] = p

    # (external_id, zip, lat, lon, default_provider, n_total_appts, n_noshows)
    established = [
        ("pat-1001", "10001", 40.748, -73.996, "prov-201",  8, 1),
        ("pat-1002", "10019", 40.776, -73.988, "prov-202", 14, 5),
        ("pat-1003", "10003", 40.706, -73.997, "prov-203",  6, 0),
        ("pat-1004", "10014", 40.739, -74.001, "prov-201", 11, 4),
    ]
    now = datetime.utcnow()

    for (ext_id, zip_code, lat, lon, prov_id, n_total, n_noshows) in established:
        pat = db.query(Patient).filter(Patient.external_id == ext_id).first()
        if pat is None:
            pat = Patient(external_id=ext_id, zip_code=zip_code, latitude=lat, longitude=lon)
            db.add(pat)
            db.flush()

        # Only seed if no seeded history already exists for this patient
        already_seeded = db.query(Appointment).filter(
            Appointment.patient_id == pat.id,
            Appointment.external_id.like(f"hist-{ext_id}-%"),
        ).count()
        if already_seeded > 0:
            continue

        prov = prov_map[prov_id]
        outcomes = [False] * n_noshows + [True] * (n_total - n_noshows)
        _rng.shuffle(outcomes)

        for i, attended in enumerate(outcomes):
            days_ago = _rng.randint(30 * (i + 1), 30 * (i + 2))
            sched = now - timedelta(days=days_ago)
            sched = sched.replace(hour=_rng.choice([9, 10, 11, 14, 15]), minute=0, second=0, microsecond=0)
            booked = sched - timedelta(days=_rng.randint(2, 14))
            lead = max((sched - booked).total_seconds() / 3600.0, 0.0)
            prior_noshows_then = sum(1 for x in outcomes[:i] if not x)
            appt_type = _rng.choice(["follow_up", "sick_visit", "annual_wellness"])
            db.add(Appointment(
                external_id=f"hist-{ext_id}-{i}",
                patient_id=pat.id,
                provider_id=prov.id,
                appointment_type=appt_type,
                is_new_patient=(i == 0),
                is_telehealth=False,
                specialty=prov.specialty,
                confirmation_channel=_rng.choice(["sms", "email"]),
                weather_code="clear",
                weather_temp_f=72.0,
                distance_miles=_rng.uniform(0.5, 14.0),
                lead_time_hours=lead,
                day_of_week=sched.weekday(),
                hour_of_day=sched.hour,
                prior_total_appts=i,
                prior_no_show_count=prior_noshows_then,
                prior_portal_logins_30d=_rng.randint(0, 8),
                prior_reminder_response_rate=_rng.uniform(0.4, 0.95),
                digital_engagement_score=_rng.uniform(0.4, 0.9),
                provider_no_show_rate=0.12,
                status="completed" if attended else "no_show",
                label_attended=attended,
                booked_at=booked,
                scheduled_at=sched,
            ))

    # Kevin Johnson (pat-1005) – new patient, just ensure Patient row exists with no appointments
    kj = db.query(Patient).filter(Patient.external_id == "pat-1005").first()
    if kj is None:
        db.add(Patient(external_id="pat-1005", zip_code="10025", latitude=40.785, longitude=-73.980))

    db.commit()


def seed_synthetic_history(db: Session, n_patients: int = 400, n_providers: int = 35, n_appointments: int = 5000) -> None:
    if db.query(Appointment).count() > 0:
        return

    random.seed(42)

    providers: list[Provider] = []
    specialties = ["primary_care", "cardiology", "orthopedics", "dermatology", "behavioral_health"]
    for i in range(n_providers):
        provider = Provider(
            external_id=f"prov-{i+1}",
            specialty=random.choice(specialties),
            latitude=40.0 + random.random(),
            longitude=-74.0 + random.random(),
        )
        db.add(provider)
        providers.append(provider)

    patients: list[Patient] = []
    for i in range(n_patients):
        patient = Patient(
            external_id=f"pat-{i+1}",
            zip_code=f"10{random.randint(100, 999)}",
            latitude=40.0 + random.random(),
            longitude=-74.0 + random.random(),
        )
        db.add(patient)
        patients.append(patient)

    db.flush()

    now = datetime.utcnow()

    for i in range(n_appointments):
        patient = random.choice(patients)
        provider = random.choice(providers)

        prior_total = random.randint(0, 20)
        prior_no_show = random.randint(0, max(prior_total, 1)) if prior_total > 0 else 0
        prior_no_show_rate = prior_no_show / prior_total if prior_total > 0 else 0.0

        booked_at = now - timedelta(days=random.randint(3, 360), hours=random.randint(0, 23))
        lead_hours = random.randint(4, 720)
        scheduled_at = booked_at + timedelta(hours=lead_hours)

        hour_of_day = random.choice([8, 9, 10, 11, 13, 14, 15, 16])
        scheduled_at = scheduled_at.replace(hour=hour_of_day, minute=0, second=0, microsecond=0)

        appointment_type = random.choice(["follow_up", "new_consult", "annual_wellness", "procedure"])
        confirmation_channel = random.choice(["sms", "email", "phone", "portal"])
        weather_code = random.choice(["clear", "rain", "snow", "wind"])
        weather_temp_f = random.uniform(20, 95)
        distance_miles = random.uniform(0.5, 30)
        portal_logins = random.randint(0, 20)
        reminder_resp = random.uniform(0.0, 1.0)
        engagement = random.uniform(0.0, 1.0)
        provider_no_show_rate = random.uniform(0.05, 0.25)
        is_new_patient = random.random() < 0.2
        is_telehealth = random.random() < 0.3

        attendance_score = 0.80
        attendance_score -= prior_no_show_rate * 0.45
        attendance_score -= min(distance_miles, 35) / 220.0
        attendance_score -= lead_hours / 3200.0
        attendance_score += reminder_resp * 0.20
        attendance_score += engagement * 0.08
        if is_telehealth:
            attendance_score += 0.05
        if hour_of_day < 9:
            attendance_score -= 0.04
        if weather_code in {"snow", "rain"} and not is_telehealth:
            attendance_score -= 0.03

        attendance_prob = max(min(attendance_score, 0.97), 0.03)
        attended = random.random() < attendance_prob

        appointment = Appointment(
            external_id=f"hist-appt-{i+1}",
            patient_id=patient.id,
            provider_id=provider.id,
            appointment_type=appointment_type,
            is_new_patient=is_new_patient,
            is_telehealth=is_telehealth,
            specialty=provider.specialty,
            confirmation_channel=confirmation_channel,
            weather_code=weather_code,
            weather_temp_f=weather_temp_f,
            distance_miles=distance_miles,
            lead_time_hours=float(lead_hours),
            day_of_week=scheduled_at.weekday(),
            hour_of_day=hour_of_day,
            prior_total_appts=prior_total,
            prior_no_show_count=prior_no_show,
            prior_portal_logins_30d=portal_logins,
            prior_reminder_response_rate=reminder_resp,
            digital_engagement_score=engagement,
            provider_no_show_rate=provider_no_show_rate,
            status="completed" if attended else "no_show",
            label_attended=attended,
            booked_at=booked_at,
            scheduled_at=scheduled_at,
        )
        db.add(appointment)

    db.commit()
