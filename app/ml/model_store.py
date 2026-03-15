import json
from datetime import datetime, UTC
from pathlib import Path

import joblib

from app.config import settings


def ensure_artifact_dir() -> None:
    Path(settings.model_path).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.feature_metadata_path).parent.mkdir(parents=True, exist_ok=True)


def save_model(model, metadata: dict) -> str:
    ensure_artifact_dir()
    model_version = datetime.now(UTC).strftime("model-%Y%m%d%H%M%S")
    metadata = {**metadata, "model_version": model_version}

    joblib.dump(model, settings.model_path)
    Path(settings.feature_metadata_path).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return model_version


def load_model_and_metadata():
    model_path = Path(settings.model_path)
    metadata_path = Path(settings.feature_metadata_path)

    if not model_path.exists() or not metadata_path.exists():
        return None, {"model_version": "heuristic-v1"}

    model = joblib.load(model_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return model, metadata
