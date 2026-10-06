import sqlite3
import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

def get_db_path() -> str:
    return os.getenv("DB_PATH", "calls.db")

def init_db(db_path: Optional[str] = None):
    path = db_path or get_db_path()
    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                call_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                duration_secs INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Logictap Call Recording Service",
    description="Idempotent webhook ingestion and call retrieval service",
    version="2.0.0",
    lifespan=lifespan
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    # Check if call_id was the missing field
    for err in errors:
        loc = err.get("loc", ())
        if "call_id" in loc:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Bad Request", "detail": "call_id is required and cannot be empty"}
            )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Bad Request", "detail": errors[0].get("msg", "Invalid request body")}
    )

class CallEndedPayload(BaseModel):
    call_id: str = Field(..., min_length=1, description="Unique call identifier")
    status: str = Field(..., min_length=1, description="Status of the call, e.g. answered, missed")
    duration_secs: int = Field(..., ge=0, description="Duration of call in seconds")

    @field_validator("call_id")
    @classmethod
    def call_id_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("call_id cannot be empty or whitespace")
        return v.strip()

def get_db_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

@app.post("/call-ended")
def record_call_ended(payload: CallEndedPayload, response: Response):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Atomic idempotency: insert only if call_id does not already exist
        cursor.execute(
            "INSERT OR IGNORE INTO calls (call_id, status, duration_secs) VALUES (?, ?, ?)",
            (payload.call_id, payload.status, payload.duration_secs)
        )
        conn.commit()

        if cursor.rowcount == 1:
            response.status_code = status.HTTP_201_CREATED
            return {
                "success": True,
                "message": "Call record created successfully",
                "call_id": payload.call_id,
                "is_duplicate": False
            }
        else:
            response.status_code = status.HTTP_200_OK
            return {
                "success": True,
                "message": "Duplicate call received; existing record preserved",
                "call_id": payload.call_id,
                "is_duplicate": True
            }
    finally:
        conn.close()

@app.get("/calls/{call_id}")
def get_call_record(call_id: str):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT call_id, status, duration_secs, created_at FROM calls WHERE call_id = ?",
            (call_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Call record with ID '{call_id}' not found"
            )
        return {
            "call_id": row["call_id"],
            "status": row["status"],
            "duration_secs": row["duration_secs"],
            "created_at": row["created_at"]
        }
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
