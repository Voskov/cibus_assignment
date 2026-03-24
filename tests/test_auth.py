import pytest
from fastapi.testclient import TestClient


# ── Register ──────────────────────────────────────────────────────────────────

def test_register_success(client: TestClient):
    resp = client.post("/register", json={"username": "alice", "password": "Secret1!"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert "id" in data
    assert "created_at" in data
    assert "password_hash" not in data


def test_register_duplicate_username(client: TestClient):
    client.post("/register", json={"username": "alice", "password": "Secret1!"})
    resp = client.post("/register", json={"username": "alice", "password": "Other1234"})
    assert resp.status_code == 409


def test_register_empty_username(client: TestClient):
    resp = client.post("/register", json={"username": "  ", "password": "Secret1!"})
    assert resp.status_code == 422


def test_register_empty_password(client: TestClient):
    resp = client.post("/register", json={"username": "alice", "password": ""})
    assert resp.status_code == 422


def test_register_password_too_short(client: TestClient):
    resp = client.post("/register", json={"username": "alice", "password": "Sec1"})
    assert resp.status_code == 422


def test_register_password_no_uppercase(client: TestClient):
    resp = client.post("/register", json={"username": "alice", "password": "secret123"})
    assert resp.status_code == 422


def test_register_password_no_digit(client: TestClient):
    resp = client.post("/register", json={"username": "alice", "password": "SecretABC"})
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_success(client: TestClient):
    client.post("/register", json={"username": "alice", "password": "Secret1!"})
    resp = client.post("/login", json={"username": "alice", "password": "Secret1!"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) == 64  # secrets.token_hex(32) → 64 hex chars


def test_login_wrong_password(client: TestClient):
    client.post("/register", json={"username": "alice", "password": "Secret1!"})
    resp = client.post("/login", json={"username": "alice", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_user(client: TestClient):
    resp = client.post("/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

def test_logout_success(auth_client: TestClient):
    resp = auth_client.post("/logout")
    assert resp.status_code == 200


def test_logout_invalidates_token(auth_client: TestClient):
    auth_client.post("/logout")
    # Token should now be gone; protected endpoint must return 401
    resp = auth_client.post("/messages", json={"content": "hello"})
    assert resp.status_code == 401


def test_logout_unauthenticated(client: TestClient):
    resp = client.post("/logout")
    assert resp.status_code == 401


def test_logout_with_invalid_token(client: TestClient):
    client.headers = {**client.headers, "Authorization": "Bearer invalidtoken"}
    resp = client.post("/logout")
    assert resp.status_code == 401
