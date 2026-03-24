import pytest
from fastapi.testclient import TestClient


class TestRegister:
    def test_success(self, client: TestClient):
        resp = client.post("/register", json={"username": "alice", "password": "Secret1!"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "alice"
        assert "id" in data
        assert "created_at" in data
        assert "password_hash" not in data

    def test_duplicate_username(self, client: TestClient):
        client.post("/register", json={"username": "alice", "password": "Secret1!"})
        resp = client.post("/register", json={"username": "alice", "password": "Other1234"})
        assert resp.status_code == 409

    def test_empty_username(self, client: TestClient):
        resp = client.post("/register", json={"username": "  ", "password": "Secret1!"})
        assert resp.status_code == 422

    def test_empty_password(self, client: TestClient):
        resp = client.post("/register", json={"username": "alice", "password": ""})
        assert resp.status_code == 422

    def test_password_too_short(self, client: TestClient):
        resp = client.post("/register", json={"username": "alice", "password": "Sec1"})
        assert resp.status_code == 422

    def test_password_no_uppercase(self, client: TestClient):
        resp = client.post("/register", json={"username": "alice", "password": "secret123"})
        assert resp.status_code == 422

    def test_password_no_digit(self, client: TestClient):
        resp = client.post("/register", json={"username": "alice", "password": "SecretABC"})
        assert resp.status_code == 422


class TestLogin:
    def test_success(self, client: TestClient):
        client.post("/register", json={"username": "alice", "password": "Secret1!"})
        resp = client.post("/login", json={"username": "alice", "password": "Secret1!"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) == 64

    def test_wrong_password(self, client: TestClient):
        client.post("/register", json={"username": "alice", "password": "Secret1!"})
        resp = client.post("/login", json={"username": "alice", "password": "wrongpass"})
        assert resp.status_code == 401

    def test_unknown_user(self, client: TestClient):
        resp = client.post("/login", json={"username": "nobody", "password": "x"})
        assert resp.status_code == 401


class TestLogout:
    def test_success(self, auth_client: TestClient):
        resp = auth_client.post("/logout")
        assert resp.status_code == 200

    def test_invalidates_token(self, auth_client: TestClient):
        auth_client.post("/logout")
        resp = auth_client.post("/messages", json={"content": "hello"})
        assert resp.status_code == 401

    def test_unauthenticated(self, client: TestClient):
        resp = client.post("/logout")
        assert resp.status_code == 401

    def test_invalid_token(self, client: TestClient):
        client.headers = {**client.headers, "Authorization": "Bearer invalidtoken"}
        resp = client.post("/logout")
        assert resp.status_code == 401
