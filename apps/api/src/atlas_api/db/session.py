from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from atlas_api.core.config import settings

engine = create_engine(settings.resolved_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
