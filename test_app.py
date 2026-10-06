import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

TEST_DB = "test_calls.db"
os.environ["DB_PATH"] = TEST_DB

from app import app, init_db

@pytest.fixture(autouse=True)
def clean_database():
    init_db(TEST_DB)
    with sqlite3.connect(TEST_DB) as conn:
        conn.execute("DELETE FROM calls")
        conn.commit()
    yield

client = TestClient(app)

def test_repeated_request_does_not_create_second_record():
    """
    Automated test ensuring idempotency:
    Sending duplicate call-ended webhooks with the same call_id
    returns success without creating duplicate database records.
    """
    payload = {
        "call_id": "abc123",
        "status": "answered",
        "duration_secs": 42
    }

    # 1. First request
    resp1 = client.post("/call-ended", json=payload)
    assert resp1.status_code in [200, 201], f"Expected 200/201, got {resp1.status_code}"
    assert resp1.json()["success"] is True

    # Check database count after first request
    with sqlite3.connect(TEST_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM calls WHERE call_id = ?", ("abc123",))
        count_after_first = cursor.fetchone()[0]
    assert count_after_first == 1, f"Expected 1 record, found {count_after_first}"

    # 2. Second request with the exact same payload
    resp2 = client.post("/call-ended", json=payload)
    assert resp2.status_code == 200, f"Expected 200 OK for duplicate, got {resp2.status_code}"
    assert resp2.json()["success"] is True

    # Check database count after second request
    with sqlite3.connect(TEST_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM calls WHERE call_id = ?", ("abc123",))
        count_after_second = cursor.fetchone()[0]
    
    # Verify that NO second record was created
    assert count_after_second == 1, f"Expected exactly 1 record, but found {count_after_second}"

def test_get_call_record():
    payload = {"call_id": "call_456", "status": "completed", "duration_secs": 18}
    client.post("/call-ended", json=payload)

    get_resp = client.get("/calls/call_456")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["call_id"] == "call_456"
    assert data["status"] == "completed"
    assert data["duration_secs"] == 18

def test_get_nonexistent_call():
    resp = client.get("/calls/nonexistent_id")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

def test_missing_call_id_rejected():
    resp = client.post("/call-ended", json={"status": "answered", "duration_secs": 10})
    assert resp.status_code == 400
    assert "call_id" in resp.json()["detail"]
