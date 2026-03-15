from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import Base, SessionLocal, engine
from app.ml.train import InsufficientTrainingDataError, train_and_persist_model
from app.seed import seed_known_patients, seed_synthetic_history


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        seed_synthetic_history(db)
        seed_known_patients(db)
        result = train_and_persist_model(db)
        print("Model trained successfully")
        print(result)
    except InsufficientTrainingDataError as exc:
        print(f"Training skipped: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
