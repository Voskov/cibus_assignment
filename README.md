# Cibus — Message Board API

A simple message board REST API built with FastAPI, SQLite, and SQLAlchemy.

---

## Setup

### Prerequisites
- Python 3.11+

### Local development

```bash
# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs (Swagger UI) are at `http://localhost:8000/docs`.
ReDoc docs are at `http://localhost:8000/redoc`.

---

## Docker

```bash
# Build the image
docker build -t cibus .

# Run the container
docker run -p 8000:8000 cibus
```

---

## Running tests

```bash
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## API Overview

### Auth

#### Register
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret"}'
```

#### Login
```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret"}'
# Returns: {"access_token": "<token>", "token_type": "bearer"}
```

#### Logout (requires auth)
```bash
curl -X POST http://localhost:8000/logout \
  -H "Authorization: Bearer <token>"
```

---

### Messages

#### List all messages (public)
```bash
curl http://localhost:8000/messages
```

#### Post a message (requires auth)
```bash
curl -X POST http://localhost:8000/messages \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello, world!"}'
```

#### Vote on a message (requires auth)
```bash
# Upvote
curl -X POST http://localhost:8000/messages/1/vote \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"value": 1}'

# Downvote
curl -X POST http://localhost:8000/messages/1/vote \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"value": -1}'
```

Voting is an **upsert**: if the user has already voted on a message, the existing vote is updated to the new value.

#### Delete a message (requires auth, author only)
```bash
curl -X DELETE http://localhost:8000/messages/1 \
  -H "Authorization: Bearer <token>"
```

#### Get current user's messages (requires auth)
```bash
curl http://localhost:8000/user/messages \
  -H "Authorization: Bearer <token>"
```

---

## Assumptions

- **Single-session logout**: `POST /logout` deletes only the token used in that specific request. A user with multiple active tokens (e.g., logged in from multiple devices) keeps the remaining tokens valid.
- **Vote count**: Computed as the arithmetic sum of all vote values for a message (`+1` votes minus `-1` votes). Returns `0` when no votes exist.
- **SQLite**: The database file `cibus.db` is created in the working directory at startup. For production use, replace with a persistent volume or a proper database like PostgreSQL.
- **Password hashing**: bcrypt via `passlib[bcrypt]` with default cost factor (12).
- **Token format**: `secrets.token_hex(32)` produces a 64-character hexadecimal string.
- **No pagination**: `GET /messages` returns all messages. Add pagination for large datasets.
- **UTC timestamps**: All `created_at` fields are stored in UTC.
