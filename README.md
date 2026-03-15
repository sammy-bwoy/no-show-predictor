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

## Deploy publicly with a cloud database

This repo is now set up for Render so the site can be viewed publicly from desktop or mobile, backed by a managed Postgres database.

### What is included

- `render.yaml` provisions:
  - a public Python web service for the FastAPI app
  - a managed PostgreSQL database
- `DATABASE_URL` automatically switches the app from local SQLite to Postgres
- `BOOTSTRAP_DEMO_DATA=true` seeds demo data and trains a model automatically on first deploy

### Deploy steps

1. Create a Render account and connect your GitHub account.
2. In Render, choose **New Blueprint Instance**.
3. Select this repository.
4. Render will detect `render.yaml` and create:
   - the web service
   - the managed Postgres database
5. Wait for the first deploy to finish.
6. Open the Render service URL. The UI is responsive and works on mobile browsers.

### Environment notes

- Local development still uses SQLite by default.
- Render will inject the Postgres connection string into `DATABASE_URL`.
- If you want an empty production environment later, set `BOOTSTRAP_DEMO_DATA=false` and remove the demo bootstrap endpoint from your workflow.

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
