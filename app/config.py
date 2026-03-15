from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_url(value: str) -> str:
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://") and not value.startswith("postgresql+psycopg://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


class Settings(BaseSettings):
    app_name: str = "No-Show Predictor"
    database_url: str = "sqlite:///./noshow.db"
    model_path: str = "artifacts/model.joblib"
    feature_metadata_path: str = "artifacts/feature_metadata.json"
    low_attendance_threshold: float = 0.50
    bootstrap_demo_data: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        return _normalize_database_url(value)


settings = Settings()
