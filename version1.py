from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# In-memory storage
calls_db = {}

class CallEndedPayload(BaseModel):
    call_id: Optional[str] = None
    status: str
    duration_secs: int

@app.post("/call-ended")
def call_ended(payload: CallEndedPayload):
    if not payload.call_id:
        raise HTTPException(status_code=400, detail="Missing call_id")
    
    if payload.call_id in calls_db:
        return {"status": "success", "message": "Call already recorded", "data": calls_db[payload.call_id]}
    
    record = payload.dict()
    calls_db[payload.call_id] = record
    return {"status": "success", "message": "Call recorded", "data": record}

@app.get("/calls/{call_id}")
def get_call(call_id: str):
    if call_id not in calls_db:
        raise HTTPException(status_code=404, detail="Call not found")
    return calls_db[call_id]
