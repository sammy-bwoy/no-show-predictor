from pathlib import Path
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db, SessionLocal
from app.ml.model_store import load_model_and_metadata
from app.ml.train import InsufficientTrainingDataError, train_and_persist_model
from app.models import Appointment, Prediction, PredictionFeedback
from app.schemas import (
    AppointmentConfirmRequest,
    AppointmentPredictionResponse,
    BookingScheduleRequest,
    BookingScheduleResponse,
    FeedbackRequest,
    OutcomeLabelRequest,
    PatientSearchResult,
    ProviderDayAvailability,
    ProviderSearchResult,
)
from app.seed import seed_known_patients, seed_synthetic_history
from app.services.actions import confidence_label
from app.services.booking_flow import (
    APPOINTMENT_TYPE_DEFAULT_DURATION,
    build_background_confirm_request,
    provider_week_availability,
    search_patients,
    search_providers,
)
from app.services.scoring import score_appointment

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def _ensure_sqlite_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as conn:
        prediction_columns = {row[1] for row in conn.execute(text("PRAGMA table_info(predictions)"))}
        if "confidence_score" not in prediction_columns:
            conn.execute(text("ALTER TABLE predictions ADD COLUMN confidence_score FLOAT DEFAULT 0.5"))
        if "insufficient_data" not in prediction_columns:
            conn.execute(text("ALTER TABLE predictions ADD COLUMN insufficient_data BOOLEAN DEFAULT 0"))

        appointment_columns = {row[1] for row in conn.execute(text("PRAGMA table_info(appointments)"))}
        if "booking_context" not in appointment_columns:
            conn.execute(text("ALTER TABLE appointments ADD COLUMN booking_context JSON"))


def _bootstrap_demo_environment() -> None:
    if not settings.bootstrap_demo_data:
        return

    db = SessionLocal()
    try:
        if db.query(Appointment.id).first() is None:
            seed_synthetic_history(db)

        seed_known_patients(db)

        model, _ = load_model_and_metadata()
        if model is None:
            train_and_persist_model(db)
    except InsufficientTrainingDataError:
        pass
    finally:
        db.close()


def _prediction_to_response(prediction: Prediction) -> AppointmentPredictionResponse:
    show_numeric = not bool(getattr(prediction, "insufficient_data", False))
    is_not_applicable = prediction.risk_band == "not_applicable"
    show_numeric = not bool(getattr(prediction, "insufficient_data", False)) and not is_not_applicable
    risk_map = {
        "high": "NO-SHOW Risk: High",
        "medium": "NO-SHOW Risk: Medium",
        "low": "NO-SHOW Risk: Low",
        "not_enough_data": "NO-SHOW Risk: Not Enough Data",
        "not_applicable": "N/A",
    }
    label = risk_map.get(prediction.risk_band, "NO-SHOW Risk: Medium")

    return AppointmentPredictionResponse(
        prediction_id=prediction.id,
        appointment_id=prediction.appointment_id,
        attendance_likelihood_pct=round(prediction.attendance_probability * 100, 2) if show_numeric else None,
        no_show_likelihood_pct=round(prediction.no_show_probability * 100, 2) if show_numeric else None,
        risk_band=prediction.risk_band,
        risk_label=label,
        confidence_score=round(prediction.confidence_score, 2),
        confidence_label=confidence_label(prediction.confidence_score),
        show_numeric_score=show_numeric,
        recommended_actions=prediction.recommended_actions,
        reason_codes=prediction.reason_codes,
        model_version=prediction.model_version,
    )


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()
    _bootstrap_demo_environment()


@app.get("/")
def serve_ui() -> FileResponse:
    index_path = static_dir / "index.html"
    return FileResponse(index_path)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@app.post("/v1/appointments/confirm", response_model=AppointmentPredictionResponse)
def confirm_appointment(payload: AppointmentConfirmRequest, db: Session = Depends(get_db)) -> AppointmentPredictionResponse:
    prediction = score_appointment(db, payload)
    return _prediction_to_response(prediction)


@app.get("/v1/booking/patients/search", response_model=list[PatientSearchResult])
def patient_search(q: str = Query(default="")) -> list[PatientSearchResult]:
    results = search_patients(q)
    return [PatientSearchResult(**row) for row in results]


@app.get("/v1/booking/providers/search", response_model=list[ProviderSearchResult])
def provider_search(q: str = Query(default="")) -> list[ProviderSearchResult]:
    results = search_providers(q)
    return [ProviderSearchResult(**row) for row in results]


@app.get("/v1/booking/providers/{provider_id}/availability", response_model=list[ProviderDayAvailability])
def provider_availability(
    provider_id: str,
    week_start: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ProviderDayAvailability]:
    parsed_week_start = None
    if week_start:
        parsed_week_start = datetime.fromisoformat(week_start)
    days = provider_week_availability(db, provider_id, week_start=parsed_week_start)
    return [ProviderDayAvailability(**day) for day in days]


@app.post("/v1/booking/schedule", response_model=BookingScheduleResponse)
def booking_schedule(payload: BookingScheduleRequest, db: Session = Depends(get_db)) -> BookingScheduleResponse:
    if payload.appointment_type in APPOINTMENT_TYPE_DEFAULT_DURATION:
        expected = APPOINTMENT_TYPE_DEFAULT_DURATION[payload.appointment_type]
        payload.duration_minutes = expected

    confirm_payload, booking_context = build_background_confirm_request(db, payload)
    prediction = score_appointment(db, confirm_payload, booking_context=booking_context)

    return BookingScheduleResponse(
        appointment_external_id=confirm_payload.appointment.external_id,
        prediction=_prediction_to_response(prediction),
    )


@app.post("/v1/predictions/{prediction_id}/feedback")
def submit_feedback(prediction_id: int, payload: FeedbackRequest, db: Session = Depends(get_db)) -> dict:
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction not found")

    feedback = PredictionFeedback(
        prediction_id=prediction.id,
        appointment_id=prediction.appointment_id,
        is_wrong=payload.is_wrong,
        reason_text=payload.reason_text,
        submitted_by=payload.submitted_by,
    )
    db.add(feedback)
    db.commit()

    return {"status": "saved", "feedback_id": feedback.id}


@app.post("/v1/appointments/{appointment_external_id}/outcome")
def update_appointment_outcome(
    appointment_external_id: str,
    payload: OutcomeLabelRequest,
    db: Session = Depends(get_db),
) -> dict:
    appointment = db.query(Appointment).filter(Appointment.external_id == appointment_external_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.label_attended = payload.attended
    appointment.status = "completed" if payload.attended else "no_show"
    db.commit()

    return {"status": "updated", "appointment_external_id": appointment_external_id}


@app.post("/v1/models/train")
def train_model(db: Session = Depends(get_db)) -> dict:
    try:
        result = train_and_persist_model(db)
        return {"status": "trained", **result}
    except InsufficientTrainingDataError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/system/bootstrap")
def bootstrap_system() -> dict:
    db = SessionLocal()
    try:
        seed_synthetic_history(db)
        result = train_and_persist_model(db)
        return {"status": "bootstrapped", **result}
    finally:
        db.close()
