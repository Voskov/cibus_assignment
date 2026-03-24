import pytest
from fastapi.testclient import TestClient


def _post_message(client: TestClient, content: str = "Hello, world!") -> dict:
    resp = client.post("/messages", json={"content": content})
    assert resp.status_code == 201
    return resp.json()


def _register_and_login(client: TestClient, username: str, password: str = "Secret1!") -> str:
    client.post("/register", json={"username": username, "password": password})
    resp = client.post("/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


class TestListMessages:
    def test_empty(self, client: TestClient):
        resp = client.get("/messages")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_all(self, auth_client: TestClient):
        _post_message(auth_client, "First")
        _post_message(auth_client, "Second")
        resp = auth_client.get("/messages")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_public_no_auth(self, client: TestClient, auth_client: TestClient):
        _post_message(auth_client, "Visible to all")
        resp = client.get("/messages")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_contains_expected_fields(self, auth_client: TestClient):
        _post_message(auth_client, "Test message")
        msg = auth_client.get("/messages").json()[0]
        assert "id" in msg
        assert "content" in msg
        assert "author_username" in msg
        assert "vote_count" in msg
        assert "created_at" in msg
        assert msg["vote_count"] == 0


class TestCreateMessage:
    def test_success(self, auth_client: TestClient):
        resp = auth_client.post("/messages", json={"content": "Hello!"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Hello!"
        assert data["author_username"] == "alice"
        assert data["vote_count"] == 0

    def test_unauthenticated(self, client: TestClient):
        resp = client.post("/messages", json={"content": "No auth"})
        assert resp.status_code == 401

    def test_empty_content(self, auth_client: TestClient):
        resp = auth_client.post("/messages", json={"content": "  "})
        assert resp.status_code == 422


class TestVote:
    def test_upvote(self, auth_client: TestClient):
        msg = _post_message(auth_client)
        resp = auth_client.post(f"/messages/{msg['id']}/vote", json={"value": 1})
        assert resp.status_code == 200
        assert resp.json()["vote_count"] == 1

    def test_downvote(self, auth_client: TestClient):
        msg = _post_message(auth_client)
        resp = auth_client.post(f"/messages/{msg['id']}/vote", json={"value": -1})
        assert resp.status_code == 200
        assert resp.json()["vote_count"] == -1

    def test_change(self, auth_client: TestClient):
        msg = _post_message(auth_client)
        auth_client.post(f"/messages/{msg['id']}/vote", json={"value": 1})
        resp = auth_client.post(f"/messages/{msg['id']}/vote", json={"value": -1})
        assert resp.status_code == 200
        assert resp.json()["vote_count"] == -1

    def test_upsert_same_value(self, auth_client: TestClient):
        msg = _post_message(auth_client)
        auth_client.post(f"/messages/{msg['id']}/vote", json={"value": 1})
        resp = auth_client.post(f"/messages/{msg['id']}/vote", json={"value": 1})
        assert resp.status_code == 200
        assert resp.json()["vote_count"] == 1

    def test_multiple_users(self, client: TestClient, auth_client: TestClient):
        msg = _post_message(auth_client)
        token_bob = _register_and_login(client, "bob")
        auth_client.post(f"/messages/{msg['id']}/vote", json={"value": 1})
        bob_headers = {"Authorization": f"Bearer {token_bob}"}
        resp = client.post(f"/messages/{msg['id']}/vote", json={"value": 1}, headers=bob_headers)
        assert resp.status_code == 200
        assert resp.json()["vote_count"] == 2

    def test_invalid_value(self, auth_client: TestClient):
        msg = _post_message(auth_client)
        resp = auth_client.post(f"/messages/{msg['id']}/vote", json={"value": 0})
        assert resp.status_code == 422

    def test_nonexistent_message(self, auth_client: TestClient):
        resp = auth_client.post("/messages/99999/vote", json={"value": 1})
        assert resp.status_code == 404

    def test_unauthenticated(self, client: TestClient, auth_client: TestClient):
        msg = _post_message(auth_client)
        resp = client.post(f"/messages/{msg['id']}/vote", json={"value": 1})
        assert resp.status_code == 401


class TestDeleteMessage:
    def test_own_message(self, auth_client: TestClient):
        msg = _post_message(auth_client)
        resp = auth_client.delete(f"/messages/{msg['id']}")
        assert resp.status_code == 204
        msgs = auth_client.get("/messages").json()
        assert all(m["id"] != msg["id"] for m in msgs)

    def test_other_users_message(self, client: TestClient, auth_client: TestClient):
        msg = _post_message(auth_client)
        token_bob = _register_and_login(client, "bob")
        bob_headers = {"Authorization": f"Bearer {token_bob}"}
        resp = client.delete(f"/messages/{msg['id']}", headers=bob_headers)
        assert resp.status_code == 403

    def test_nonexistent_message(self, auth_client: TestClient):
        resp = auth_client.delete("/messages/99999")
        assert resp.status_code == 404

    def test_unauthenticated(self, client: TestClient, auth_client: TestClient):
        msg = _post_message(auth_client)
        resp = client.delete(f"/messages/{msg['id']}")
        assert resp.status_code == 401


class TestMyMessages:
    def test_empty(self, auth_client: TestClient):
        resp = auth_client.get("/user/messages")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_only_mine(self, client: TestClient, auth_client: TestClient):
        _post_message(auth_client, "Alice's post")
        token_bob = _register_and_login(client, "bob")
        bob_headers = {"Authorization": f"Bearer {token_bob}"}
        client.post("/messages", json={"content": "Bob's post"}, headers=bob_headers)
        resp = auth_client.get("/user/messages")
        assert resp.status_code == 200
        msgs = resp.json()
        assert len(msgs) == 1
        assert msgs[0]["author_username"] == "alice"

    def test_unauthenticated(self, client: TestClient):
        resp = client.get("/user/messages")
        assert resp.status_code == 401

    def test_vote_count(self, auth_client: TestClient, client: TestClient):
        msg = _post_message(auth_client)
        token_bob = _register_and_login(client, "bob")
        bob_headers = {"Authorization": f"Bearer {token_bob}"}
        client.post(f"/messages/{msg['id']}/vote", json={"value": 1}, headers=bob_headers)
        resp = auth_client.get("/user/messages")
        assert resp.json()[0]["vote_count"] == 1
