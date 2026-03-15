from app.config import settings


def classify_risk_band(attendance_probability: float) -> str:
    if attendance_probability < 0.50:
        return "high"
    if attendance_probability < 0.80:
        return "medium"
    return "low"


def recommend_actions(attendance_probability: float) -> list[str]:
    if attendance_probability < settings.low_attendance_threshold:
        return [
            "add_double_booking_candidate",
            "send_additional_reminders",
            "notify_patient_contacts",
            "ignore_for_now",
        ]
    return ["proceed_with_standard_workflow"]


def recommend_actions_for_insufficient_data() -> list[str]:
    return ["proceed_with_standard_workflow"]


def confidence_label(confidence_score: float) -> str:
    if confidence_score >= 0.75:
        return "high"
    if confidence_score >= 0.50:
        return "medium"
    return "low"


def build_reason_codes(feature_row: dict) -> list[str]:
    reasons: list[str] = []

    if feature_row["prior_no_show_rate"] >= 0.30:
        reasons.append("high_historical_no_show_rate")
    if feature_row["distance_miles"] >= 15 and feature_row["is_telehealth"] == 0:
        reasons.append("long_travel_distance")
    if feature_row["lead_time_hours"] >= 336:
        reasons.append("long_lead_time_before_visit")
    if feature_row["prior_reminder_response_rate"] < 0.40:
        reasons.append("low_reminder_response_history")
    if feature_row["digital_engagement_score"] < 0.35:
        reasons.append("low_digital_engagement")
    if feature_row["hour_of_day"] < 9:
        reasons.append("early_morning_slot")

    if not reasons:
        reasons.append("stable_engagement_pattern")

    return reasons
