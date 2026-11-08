import os
os.environ["DATABASE_URL"] = "sqlite:///./test_trustvault.db"
os.environ["UPLOAD_DIR"] = "./test_uploads"
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
import pytest

@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
