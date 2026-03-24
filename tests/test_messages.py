import pytest
from fastapi.testclient import TestClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _post_message(client: TestClient, content: str = "Hello, world!") -> dict:
    resp = client.post("/messages", json={"content": content})
    assert resp.status_code == 201
    return resp.json()


def _register_and_login(client: TestClient, username: str, password: str = "Secret1!") -> str:
    client.post("/register", json={"username": username, "password": password})
    resp = client.post("/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


# ── GET /messages (public) ────────────────────────────────────────────────────

def test_list_messages_empty(client: TestClient):
    resp = client.get("/messages")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_messages_returns_all(auth_client: TestClient):
    _post_message(auth_client, "First")
    _post_message(auth_client, "Second")
    resp = auth_client.get("/messages")
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) == 2


def test_list_messages_public_no_auth(client: TestClient, auth_client: TestClient):
    _post_message(auth_client, "Visible to all")
    resp = client.get("/messages")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_messages_contains_expected_fields(auth_client: TestClient):
    _post_message(auth_client, "Test message")
    resp = auth_client.get("/messages")
    msg = resp.json()[0]
    assert "id" in msg
    assert "content" in msg
    assert "author_username" in msg
    assert "vote_count" in msg
    assert "created_at" in msg
    assert msg["vote_count"] == 0


# ── POST /messages ─────────────────────────────────────────────────────────────

def test_create_message_success(auth_client: TestClient):
    resp = auth_client.post("/messages", json={"content": "Hello!"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Hello!"
    assert data["author_username"] == "alice"
    assert data["vote_count"] == 0


def test_create_message_unauthenticated(client: TestClient):
    resp = client.post("/messages", json={"content": "No auth"})
    assert resp.status_code == 401


def test_create_message_empty_content(auth_client: TestClient):
    resp = auth_client.post("/messages", json={"content": "  "})
    assert resp.status_code == 422


# ── POST /messages/{id}/vote ──────────────────────────────────────────────────

def test_vote_upvote(auth_client: TestClient):
    msg = _post_message(auth_client)
    resp = auth_client.post(f"/messages/{msg['id']}/vote", json={"value": 1})
    assert resp.status_code == 200
    assert resp.json()["vote_count"] == 1


def test_vote_downvote(auth_client: TestClient):
    msg = _post_message(auth_client)
    resp = auth_client.post(f"/messages/{msg['id']}/vote", json={"value": -1})
    assert resp.status_code == 200
    assert resp.json()["vote_count"] == -1


def test_vote_change(auth_client: TestClient):
    msg = _post_message(auth_client)
    auth_client.post(f"/messages/{msg['id']}/vote", json={"value": 1})
    resp = auth_client.post(f"/messages/{msg['id']}/vote", json={"value": -1})
    assert resp.status_code == 200
    assert resp.json()["vote_count"] == -1


def test_vote_upsert_same_value(auth_client: TestClient):
    msg = _post_message(auth_client)
    auth_client.post(f"/messages/{msg['id']}/vote", json={"value": 1})
    resp = auth_client.post(f"/messages/{msg['id']}/vote", json={"value": 1})
    assert resp.status_code == 200
    assert resp.json()["vote_count"] == 1  # still 1, not 2


def test_vote_multiple_users(client: TestClient, auth_client: TestClient):
    msg = _post_message(auth_client)

    token_bob = _register_and_login(client, "bob")
    # Vote as alice
    auth_client.post(f"/messages/{msg['id']}/vote", json={"value": 1})
    # Vote as bob using a separate client with bob's token
    bob_headers = {"Authorization": f"Bearer {token_bob}"}
    resp = client.post(f"/messages/{msg['id']}/vote", json={"value": 1}, headers=bob_headers)
    assert resp.status_code == 200
    assert resp.json()["vote_count"] == 2


def test_vote_invalid_value(auth_client: TestClient):
    msg = _post_message(auth_client)
    resp = auth_client.post(f"/messages/{msg['id']}/vote", json={"value": 0})
    assert resp.status_code == 422


def test_vote_nonexistent_message(auth_client: TestClient):
    resp = auth_client.post("/messages/99999/vote", json={"value": 1})
    assert resp.status_code == 404


def test_vote_unauthenticated(client: TestClient, auth_client: TestClient):
    msg = _post_message(auth_client)
    resp = client.post(f"/messages/{msg['id']}/vote", json={"value": 1})
    assert resp.status_code == 401


# ── DELETE /messages/{id} ─────────────────────────────────────────────────────

def test_delete_own_message(auth_client: TestClient):
    msg = _post_message(auth_client)
    resp = auth_client.delete(f"/messages/{msg['id']}")
    assert resp.status_code == 204
    # Verify it's gone
    msgs = auth_client.get("/messages").json()
    assert all(m["id"] != msg["id"] for m in msgs)


def test_delete_other_users_message(client: TestClient, auth_client: TestClient):
    msg = _post_message(auth_client)

    token_bob = _register_and_login(client, "bob")
    bob_headers = {"Authorization": f"Bearer {token_bob}"}
    resp = client.delete(f"/messages/{msg['id']}", headers=bob_headers)
    assert resp.status_code == 403


def test_delete_nonexistent_message(auth_client: TestClient):
    resp = auth_client.delete("/messages/99999")
    assert resp.status_code == 404


def test_delete_unauthenticated(client: TestClient, auth_client: TestClient):
    msg = _post_message(auth_client)
    resp = client.delete(f"/messages/{msg['id']}")
    assert resp.status_code == 401


# ── GET /user/messages ────────────────────────────────────────────────────────

def test_get_my_messages_empty(auth_client: TestClient):
    resp = auth_client.get("/user/messages")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_my_messages_returns_only_mine(client: TestClient, auth_client: TestClient):
    _post_message(auth_client, "Alice's post")

    token_bob = _register_and_login(client, "bob")
    bob_headers = {"Authorization": f"Bearer {token_bob}"}
    client.post("/messages", json={"content": "Bob's post"}, headers=bob_headers)

    resp = auth_client.get("/user/messages")
    assert resp.status_code == 200
    msgs = resp.json()
    assert len(msgs) == 1
    assert msgs[0]["author_username"] == "alice"


def test_get_my_messages_unauthenticated(client: TestClient):
    resp = client.get("/user/messages")
    assert resp.status_code == 401


def test_get_my_messages_vote_count(auth_client: TestClient, client: TestClient):
    msg = _post_message(auth_client)
    token_bob = _register_and_login(client, "bob")
    bob_headers = {"Authorization": f"Bearer {token_bob}"}
    client.post(f"/messages/{msg['id']}/vote", json={"value": 1}, headers=bob_headers)

    resp = auth_client.get("/user/messages")
    assert resp.json()[0]["vote_count"] == 1
