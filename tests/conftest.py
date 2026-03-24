import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# Use a separate file-based test DB so it can be fully reset between sessions.
# An in-memory DB (:memory:) is also fine but requires extra care with
# threading in some environments; a named file keeps things simple.
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
    """Drop and recreate all tables before each test for full isolation."""
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
    """TestClient with a pre-authenticated user (alice) token set in headers.
    Returns a separate client so the original `client` fixture stays unauthenticated."""
    client.post("/register", json={"username": "alice", "password": "Secret1!"})
    resp = client.post("/login", json={"username": "alice", "password": "Secret1!"})
    token = resp.json()["access_token"]
    # Dependency override is set on `app`, so a new TestClient also uses the test DB.
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
def second_auth_client(client: TestClient):
    """A second independently authenticated user (bob)."""
    client.post("/register", json={"username": "bob", "password": "Password1!"})
    resp = client.post("/login", json={"username": "bob", "password": "Password1!"})
    token = resp.json()["access_token"]
    # Return a new client wrapper with bob's token
    from copy import copy
    bob_client = copy(client)
    bob_client.headers = {**client.headers, "Authorization": f"Bearer {token}"}
    return bob_client
