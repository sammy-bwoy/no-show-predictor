from math import asin, cos, radians, sin, sqrt

import pandas as pd

NUMERIC_FEATURES = [
    "prior_total_appts",
    "prior_no_show_count",
    "prior_no_show_rate",
    "prior_portal_logins_30d",
    "prior_reminder_response_rate",
    "digital_engagement_score",
    "provider_no_show_rate",
    "distance_miles",
    "lead_time_hours",
    "day_of_week",
    "hour_of_day",
    "weather_temp_f",
    "is_new_patient",
    "is_telehealth",
]

CATEGORICAL_FEATURES = [
    "appointment_type",
    "confirmation_channel",
    "weather_code",
    "specialty",
]

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3958.8
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return r * c


def _resolve_distance(raw: dict) -> float:
    if raw.get("distance_miles") is not None:
        return float(raw["distance_miles"])

    patient_lat = raw.get("patient_latitude")
    patient_lon = raw.get("patient_longitude")
    provider_lat = raw.get("provider_latitude")
    provider_lon = raw.get("provider_longitude")

    if None not in (patient_lat, patient_lon, provider_lat, provider_lon):
        return float(haversine_miles(patient_lat, patient_lon, provider_lat, provider_lon))

    return 5.0


def build_feature_row(raw: dict) -> dict:
    total = max(int(raw.get("prior_total_appts", 0)), 0)
    no_show = max(int(raw.get("prior_no_show_count", 0)), 0)
    prior_no_show_rate = float(no_show / total) if total > 0 else 0.0

    row = {
        "prior_total_appts": total,
        "prior_no_show_count": no_show,
        "prior_no_show_rate": prior_no_show_rate,
        "prior_portal_logins_30d": int(raw.get("prior_portal_logins_30d", 0)),
        "prior_reminder_response_rate": float(raw.get("prior_reminder_response_rate", 0.0)),
        "digital_engagement_score": float(raw.get("digital_engagement_score", 0.0)),
        "provider_no_show_rate": float(raw.get("provider_no_show_rate", 0.10)),
        "distance_miles": _resolve_distance(raw),
        "lead_time_hours": float(raw.get("lead_time_hours", 24.0)),
        "day_of_week": int(raw.get("day_of_week", 0)),
        "hour_of_day": int(raw.get("hour_of_day", 9)),
        "weather_temp_f": float(raw.get("weather_temp_f", 72.0)),
        "is_new_patient": 1 if bool(raw.get("is_new_patient", False)) else 0,
        "is_telehealth": 1 if bool(raw.get("is_telehealth", False)) else 0,
        "appointment_type": str(raw.get("appointment_type", "follow_up")),
        "confirmation_channel": str(raw.get("confirmation_channel", "sms")),
        "weather_code": str(raw.get("weather_code", "clear")),
        "specialty": str(raw.get("specialty", "general")),
    }
    return row


def to_dataframe(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    return frame[ALL_FEATURES]
