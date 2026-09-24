"""Engine and session dependency for FastAPI."""
from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import get_settings

settings = get_settings()

# `future=True`/pool_pre_ping avoids stale connections after DB restarts (Railway).
engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
