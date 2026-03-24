import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_cibus.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client: TestClient):
    client.post("/register", json={"username": "alice", "password": "Secret1!"})
    resp = client.post("/login", json={"username": "alice", "password": "Secret1!"})
    token = resp.json()["access_token"]
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
def second_auth_client(client: TestClient):
    client.post("/register", json={"username": "bob", "password": "Password1!"})
    resp = client.post("/login", json={"username": "bob", "password": "Password1!"})
    token = resp.json()["access_token"]
    from copy import copy
    bob_client = copy(client)
    bob_client.headers = {**client.headers, "Authorization": f"Bearer {token}"}
    return bob_client
