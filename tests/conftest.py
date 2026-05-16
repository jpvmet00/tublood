import os
import pytest
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
_DB_URL = f"sqlite:///{_tmp_db.name}"

os.environ["DATABASE_URL"] = _DB_URL
os.environ["DATA_DIR"] = str(Path(__file__).parent / "fixtures")

from app.db.models import Base
import app.db.session as _session_module
from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient

_TEST_ENGINE = create_engine(_DB_URL, connect_args={"check_same_thread": False})
_TestSession = sessionmaker(bind=_TEST_ENGINE)

# Patch session module so the app uses the test engine
_session_module.engine = _TEST_ENGINE
_session_module.SessionLocal = _TestSession


@pytest.fixture(scope="function")
def db() -> Session:
    Base.metadata.create_all(bind=_TEST_ENGINE)
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=_TEST_ENGINE)


@pytest.fixture(scope="function")
def client(db: Session):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
