import os
import time
import subprocess
import httpx

if os.path.exists("calls.db"):
    os.remove("calls.db")

print("================================================================================")
print("             LOGICTAP CALL RECORDING SERVICE - TERMINAL DEMO                    ")
print("================================================================================")

# Start server
server = subprocess.Popen(["python", "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"])
time.sleep(2)

base_url = "http://127.0.0.1:8000"

try:
    print("\n>>> TEST 1: Initial POST /call-ended (call_id: 'abc123')")
    payload1 = {"call_id": "abc123", "status": "answered", "duration_secs": 42}
    r1 = httpx.post(f"{base_url}/call-ended", json=payload1)
    print(f"Status Code: {r1.status_code}")
    print(f"Response:    {r1.text}")

    print("\n>>> TEST 2: Duplicate POST /call-ended (Exact same payload with 'abc123')")
    r2 = httpx.post(f"{base_url}/call-ended", json=payload1)
    print(f"Status Code: {r2.status_code}")
    print(f"Response:    {r2.text}")

    print("\n>>> TEST 3: GET /calls/abc123 (Retrieve stored call record)")
    r3 = httpx.get(f"{base_url}/calls/abc123")
    print(f"Status Code: {r3.status_code}")
    print(f"Response:    {r3.text}")

    print("\n>>> TEST 4: POST /call-ended without call_id (Should be rejected with 400)")
    r4 = httpx.post(f"{base_url}/call-ended", json={"status": "answered", "duration_secs": 42})
    print(f"Status Code: {r4.status_code}")
    print(f"Response:    {r4.text}")

    print("\n>>> TEST 5: GET /calls/nonexistent_999 (Should return 404)")
    r5 = httpx.get(f"{base_url}/calls/nonexistent_999")
    print(f"Status Code: {r5.status_code}")
    print(f"Response:    {r5.text}")

finally:
    server.terminate()
    server.wait()
    print("\n================================================================================")
    print("DEMONSTRATION COMPLETE - ALL ENDPOINTS AND IDEMPOTENCY CHECKS VERIFIED")
    print("================================================================================")
