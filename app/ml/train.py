from datetime import UTC, datetime

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy.orm import Session

from app.ml.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES, build_feature_row, to_dataframe
from app.ml.model_store import save_model
from app.models import Appointment


class InsufficientTrainingDataError(RuntimeError):
    pass


def _load_training_frame(db: Session) -> tuple[pd.DataFrame, pd.Series]:
    labeled_rows = (
        db.query(Appointment)
        .filter(Appointment.label_attended.isnot(None))
        .order_by(Appointment.scheduled_at.asc())
        .all()
    )

    if len(labeled_rows) < 100:
        raise InsufficientTrainingDataError("Need at least 100 labeled appointments to train a reliable model.")

    features = []
    labels = []

    for appt in labeled_rows:
        features.append(
            build_feature_row(
                {
                    "prior_total_appts": appt.prior_total_appts,
                    "prior_no_show_count": appt.prior_no_show_count,
                    "prior_portal_logins_30d": appt.prior_portal_logins_30d,
                    "prior_reminder_response_rate": appt.prior_reminder_response_rate,
                    "digital_engagement_score": appt.digital_engagement_score,
                    "provider_no_show_rate": appt.provider_no_show_rate,
                    "distance_miles": appt.distance_miles,
                    "lead_time_hours": appt.lead_time_hours,
                    "day_of_week": appt.day_of_week,
                    "hour_of_day": appt.hour_of_day,
                    "weather_temp_f": appt.weather_temp_f,
                    "is_new_patient": appt.is_new_patient,
                    "is_telehealth": appt.is_telehealth,
                    "appointment_type": appt.appointment_type,
                    "confirmation_channel": appt.confirmation_channel,
                    "weather_code": appt.weather_code,
                    "specialty": appt.specialty,
                }
            )
        )
        labels.append(1 if bool(appt.label_attended) else 0)

    x = to_dataframe(features)
    y = pd.Series(labels)
    return x, y


def train_and_persist_model(db: Session) -> dict:
    x, y = _load_training_frame(db)

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocess = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, NUMERIC_FEATURES),
            ("cat", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocess", preprocess),
            (
                "classifier",
                LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs"),
            ),
        ]
    )

    model.fit(x, y)

    metadata = {
        "trained_at": datetime.now(UTC).isoformat(),
        "rows": len(x),
        "positive_rate": float(y.mean()),
        "features": list(x.columns),
        "target": "label_attended",
    }

    model_version = save_model(model, metadata)
    return {
        "model_version": model_version,
        "rows": len(x),
        "positive_rate": float(y.mean()),
    }
