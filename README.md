# No-Show Predictor (US Healthcare Appointment Flow)

This project provides an end-to-end MVP for predicting whether a patient will attend the next appointment and returning operational actions during booking confirmation.

## What is implemented

- Real-time prediction API for booking confirmation.
- Booking journey UI with:
  - patient search by ID or name
  - provider search
  - weekly provider availability and slot selection
  - appointment type with auto duration
  - additional booking fields (urgent care, insurance, referral, interpreter, contact details, notes)
- Background feature derivation so users do not manually enter distance, prior no-shows, or engagement history.
- Subtle confirmation screen that shows:
  - a no-show risk bar without numeric percentages
  - confidence label
  - risk label (high/medium/low/not enough data)
- Forced `not_enough_data` result for first-time/new-patient bookings.
- Policy actions for low attendance risk:
  - add double booking candidate
  - send additional reminders
  - notify patient contacts
  - ignore for now
- Feedback API to capture "this seems wrong" plus free-text reason.
- Outcome labeling API to store attended/no-show outcomes for retraining.
- Model training pipeline from historical data.
- Synthetic data bootstrap flow for quick local startup.

## Architecture

- `app/main.py`: FastAPI app and endpoints.
- `app/models.py`: SQLAlchemy tables for patients, providers, appointments, predictions, and feedback.
- `app/services/scoring.py`: booking-confirmation scoring flow and persistence.
- `app/ml/train.py`: supervised model training (`label_attended` target).
- `app/ml/features.py`: feature engineering and distance fallback.
- `app/static/index.html`: minimal booking confirmation UI.

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) copy `.env.example` to `.env` and adjust settings.
4. Bootstrap with synthetic history + train model:

```bash
python scripts/train_model.py
```

5. Start API server:

```bash
uvicorn app.main:app --reload
```

6. Open `http://127.0.0.1:8000`.

## Key API endpoints

- `GET /v1/booking/patients/search?q=...`
  - Finds patients by ID or partial name (for example: Yadav).
- `GET /v1/booking/providers/search?q=...`
  - Finds providers by ID, name, or specialty.
- `GET /v1/booking/providers/{provider_id}/availability`
  - Returns upcoming 7-day slot availability.
- `POST /v1/booking/schedule`
  - Schedules the appointment and immediately returns prediction for confirmation UI.
- `POST /v1/appointments/confirm`
  - Direct scoring endpoint for external workflow integrations.
- `POST /v1/predictions/{prediction_id}/feedback`
  - Stores user feedback when prediction seems wrong.
- `POST /v1/appointments/{appointment_external_id}/outcome`
  - Writes ground truth attended/no-show label.
- `POST /v1/models/train`
  - Retrains model from labeled appointments.
- `POST /v1/system/bootstrap`
  - Seeds synthetic history and trains a model quickly.

## Notes for production hardening

- Replace synthetic seed with Athenahealth and other EHR/PM integrations.
- Add HIPAA-grade controls (RBAC, audit logs, encryption, BAA-compliant deployment).
- Add feature store and event bus for high-scale multi-practice use.
- Add calibration, fairness monitoring, and drift detection dashboards.
- Add policy guardrails for double-booking by specialty/capacity constraints.
