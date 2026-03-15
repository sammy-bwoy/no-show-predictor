from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "No-Show Predictor"
    database_url: str = "sqlite:///./noshow.db"
    model_path: str = "artifacts/model.joblib"
    feature_metadata_path: str = "artifacts/feature_metadata.json"
    low_attendance_threshold: float = 0.50

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
