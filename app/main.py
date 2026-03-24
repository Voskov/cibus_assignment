from fastapi import FastAPI

from app.database import Base, engine
from app.routers import auth, messages

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Cibus Message Board",
    description="A simple message board API with auth, messages, and voting.",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(messages.router)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "service": "cibus-message-board"}
