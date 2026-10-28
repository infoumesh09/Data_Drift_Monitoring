from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from ..config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.BACKEND_ENV == "development",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from ..models import user, pipeline, dataset, feature, drift_event, schema_change, incident, experiment, ai_diagnosis
    Base.metadata.create_all(bind=engine)
