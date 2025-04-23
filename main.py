import json
import os
import requests
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Event Service", description="Service for managing events")

# Data models
class Event(BaseModel):
    id: int
    judul: str
    lokasi: str
    tanggal: str

class EventCreate(BaseModel):
    judul: str
    lokasi: str
    tanggal: str

class TicketStatus(BaseModel):
    tersedia: int
    dipesan: int
    habis: bool

# Helper functions
def load_events():
    try:
        with open("events.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_events(events):
    with open("events.json", "w") as f:
        json.dump(events, f, indent=2)

# API endpoints - Provider role
@app.get("/events", response_model=List[Event], tags=["Events"])
async def get_events():
    """
    Mengembalikan semua event aktif.
    """
    return load_events()

@app.get("/event/{id}", response_model=Event, tags=["Events"])
async def get_event(id: int):
    """
    Detail event berdasarkan ID.
    """
    events = load_events()
    for event in events:
        if event["id"] == id:
            return event
    raise HTTPException(status_code=404, detail="Event tidak ditemukan")

@app.post("/event", response_model=Event, tags=["Events"])
async def create_event(event: EventCreate):
    """
    Membuat event baru.
    """
    events = load_events()
    
    # Generate new ID
    event_id = 1
    if events:
        event_id = max(e["id"] for e in events) + 1
        
    new_event = event.model_dump()
    new_event["id"] = event_id
    events.append(new_event)
    
    save_events(events)
    return new_event

@app.put("/event/{id}", response_model=Event, tags=["Events"])
async def update_event(id: int, event_data: EventCreate):
    """
    Memperbarui event berdasarkan ID.
    """
    events = load_events()
    for i, event in enumerate(events):
        if event["id"] == id:
            updated_event = event_data.model_dump()
            updated_event["id"] = id
            events[i] = updated_event
            save_events(events)
            return updated_event
    raise HTTPException(status_code=404, detail="Event tidak ditemukan")

@app.delete("/event/{id}", tags=["Events"])
async def delete_event(id: int):
    """
    Menghapus event berdasarkan ID.
    """
    events = load_events()
    
    # Check if event exists
    event_exists = any(event["id"] == id for event in events)
    if not event_exists:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")
    
    # Filter out the event with the given ID
    updated_events = [event for event in events if event["id"] != id]
    save_events(updated_events)
    
    return {"message": "Event berhasil dihapus"}

# Consumer role - interacting with Ticket Service
@app.get("/tickets-status/{event_id}", response_model=TicketStatus, tags=["Ticket Status"])
async def get_tickets_status(event_id: int):
    """
    Mendapatkan status tiket untuk suatu event (mengkonsumsi Ticket Service).
    """
    # First verify that event exists
    events = load_events()
    event_exists = any(event["id"] == event_id for event in events)
    if not event_exists:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")
    
    # Request ticket status from Ticket Service
    ticket_service_url = "http://localhost:8001/tickets"
    try:
        response = requests.get(f"{ticket_service_url}/{event_id}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Gagal berkomunikasi dengan Ticket Service: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
