from datetime import datetime

from sqlalchemy.orm import Session

from app.ml.features import build_feature_row, to_dataframe
from app.ml.model_store import load_model_and_metadata
from app.models import Appointment, Patient, Prediction, Provider
from app.schemas import AppointmentConfirmRequest
from app.services.actions import (
    build_reason_codes,
    classify_risk_band,
    recommend_actions,
    recommend_actions_for_insufficient_data,
)


def _get_or_create_patient(db: Session, payload: AppointmentConfirmRequest) -> Patient:
    patient = db.query(Patient).filter(Patient.external_id == payload.patient.external_id).first()
    if patient is None:
        patient = Patient(external_id=payload.patient.external_id)
        db.add(patient)

    patient.zip_code = payload.patient.zip_code
    patient.latitude = payload.patient.latitude
    patient.longitude = payload.patient.longitude
    db.flush()
    return patient


def _get_or_create_provider(db: Session, payload: AppointmentConfirmRequest) -> Provider:
    provider = db.query(Provider).filter(Provider.external_id == payload.provider.external_id).first()
    if provider is None:
        provider = Provider(external_id=payload.provider.external_id)
        db.add(provider)

    provider.specialty = payload.provider.specialty
    provider.latitude = payload.provider.latitude
    provider.longitude = payload.provider.longitude
    db.flush()
    return provider


def _upsert_appointment(
    db: Session,
    payload: AppointmentConfirmRequest,
    patient_id: int,
    provider_id: int,
    booking_context: dict | None = None,
) -> Appointment:
    appointment = db.query(Appointment).filter(Appointment.external_id == payload.appointment.external_id).first()
    if appointment is None:
        appointment = Appointment(external_id=payload.appointment.external_id, patient_id=patient_id, provider_id=provider_id)
        db.add(appointment)

    booked_at = payload.appointment.booked_at
    scheduled_at = payload.appointment.scheduled_at

    lead_time_hours = max((scheduled_at - booked_at).total_seconds() / 3600.0, 0.0)

    appointment.patient_id = patient_id
    appointment.provider_id = provider_id
    appointment.appointment_type = payload.appointment.appointment_type
    appointment.is_new_patient = payload.appointment.is_new_patient
    appointment.is_telehealth = payload.appointment.is_telehealth
    appointment.specialty = payload.provider.specialty
    appointment.confirmation_channel = payload.appointment.confirmation_channel
    appointment.weather_code = payload.appointment.weather_code
    appointment.weather_temp_f = payload.appointment.weather_temp_f
    appointment.distance_miles = payload.appointment.distance_miles or 0.0

    appointment.lead_time_hours = lead_time_hours
    appointment.day_of_week = scheduled_at.weekday()
    appointment.hour_of_day = scheduled_at.hour

    appointment.prior_total_appts = payload.patient.prior_total_appts
    appointment.prior_no_show_count = payload.patient.prior_no_show_count
    appointment.prior_portal_logins_30d = payload.patient.prior_portal_logins_30d
    appointment.prior_reminder_response_rate = payload.patient.prior_reminder_response_rate
    appointment.digital_engagement_score = payload.patient.digital_engagement_score
    appointment.provider_no_show_rate = payload.provider.provider_no_show_rate

    appointment.booked_at = booked_at
    appointment.scheduled_at = scheduled_at
    appointment.status = "confirmed"
    appointment.booking_context = booking_context

    db.flush()
    return appointment


def _heuristic_attendance_probability(feature_row: dict) -> float:
    score = 0.75
    score -= feature_row["prior_no_show_rate"] * 0.35
    score -= min(feature_row["distance_miles"], 40) / 200.0
    score -= min(feature_row["lead_time_hours"], 720) / 3000.0
    score += feature_row["prior_reminder_response_rate"] * 0.20
    score += feature_row["digital_engagement_score"] * 0.10

    if feature_row["is_telehealth"] == 1:
        score += 0.04
    if feature_row["hour_of_day"] < 9:
        score -= 0.03

    return max(min(score, 0.98), 0.02)


def score_appointment(db: Session, payload: AppointmentConfirmRequest, booking_context: dict | None = None) -> Prediction:
    patient = _get_or_create_patient(db, payload)
    provider = _get_or_create_provider(db, payload)
    appointment = _upsert_appointment(db, payload, patient.id, provider.id, booking_context=booking_context)

    feature_row = build_feature_row(
        {
            "prior_total_appts": payload.patient.prior_total_appts,
            "prior_no_show_count": payload.patient.prior_no_show_count,
            "prior_portal_logins_30d": payload.patient.prior_portal_logins_30d,
            "prior_reminder_response_rate": payload.patient.prior_reminder_response_rate,
            "digital_engagement_score": payload.patient.digital_engagement_score,
            "provider_no_show_rate": payload.provider.provider_no_show_rate,
            "distance_miles": payload.appointment.distance_miles,
            "patient_latitude": payload.patient.latitude,
            "patient_longitude": payload.patient.longitude,
            "provider_latitude": payload.provider.latitude,
            "provider_longitude": payload.provider.longitude,
            "lead_time_hours": appointment.lead_time_hours,
            "day_of_week": appointment.day_of_week,
            "hour_of_day": appointment.hour_of_day,
            "weather_temp_f": payload.appointment.weather_temp_f,
            "is_new_patient": payload.appointment.is_new_patient,
            "is_telehealth": payload.appointment.is_telehealth,
            "appointment_type": payload.appointment.appointment_type,
            "confirmation_channel": payload.appointment.confirmation_channel,
            "weather_code": payload.appointment.weather_code,
            "specialty": payload.provider.specialty,
        }
    )

    if bool(payload.appointment.is_telehealth):
        prediction = Prediction(
            appointment_id=appointment.id,
            attendance_probability=0.5,
            no_show_probability=0.5,
            risk_band="not_applicable",
            confidence_score=0.0,
            insufficient_data=False,
            recommended_actions=["telehealth_visit_no_prediction_required"],
            reason_codes=["telehealth_not_scored"],
            model_version="not_applicable",
            trigger_source=payload.trigger_source,
            predicted_at=datetime.utcnow(),
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        return prediction

    insufficient_data = bool(payload.appointment.is_new_patient) or payload.patient.prior_total_appts == 0

    model, metadata = load_model_and_metadata()
    if insufficient_data:
        attendance_probability = 0.50
        model_version = metadata.get("model_version", "insufficient-data")
        confidence_score = 0.20
        risk_band = "not_enough_data"
        actions = recommend_actions_for_insufficient_data()
        reasons = ["new_patient_or_no_historical_appointments"]
    elif model is None:
        attendance_probability = _heuristic_attendance_probability(feature_row)
        model_version = metadata.get("model_version", "heuristic-v1")
        confidence_score = 0.60
    else:
        frame = to_dataframe([feature_row])
        attendance_probability = float(model.predict_proba(frame)[0][1])
        model_version = metadata.get("model_version", "unknown")
        confidence_score = 0.82

    no_show_probability = 1.0 - attendance_probability
    if not insufficient_data:
        risk_band = classify_risk_band(attendance_probability)
        actions = recommend_actions(attendance_probability)
        reasons = build_reason_codes(feature_row)

    prediction = Prediction(
        appointment_id=appointment.id,
        attendance_probability=attendance_probability,
        no_show_probability=no_show_probability,
        risk_band=risk_band,
        confidence_score=confidence_score,
        insufficient_data=insufficient_data,
        recommended_actions=actions,
        reason_codes=reasons,
        model_version=model_version,
        trigger_source=payload.trigger_source,
        predicted_at=datetime.utcnow(),
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return prediction
