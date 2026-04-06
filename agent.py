"""
agent.py — NEXA Hospital Appointment Assistant
"""

import os, sys, random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

sys.path.insert(0, os.path.dirname(__file__))
from database import init_db, db_save_meeting, db_add_task, db_get_tasks

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
model_name = os.getenv("MODEL", "gemini-2.0-flash")
init_db()

IST = timezone(timedelta(hours=5, minutes=30))

DOCTORS_DB = {
    "Dr. Kavitha Reddy": {
        "specialty": "Dermatology", "department": "Dermatology",
        "qualification": "MBBS, MD Dermatology", "experience": "12 years",
        "languages": ["English", "Telugu", "Hindi"], "fee": "₹500", "rating": 4.8,
        "slots": {
            "Monday":    ["09:00 AM","10:00 AM","11:00 AM","02:00 PM","03:00 PM","04:00 PM"],
            "Tuesday":   ["09:00 AM","10:00 AM","11:00 AM","02:00 PM","04:00 PM"],
            "Wednesday": ["10:00 AM","11:00 AM","03:00 PM","04:00 PM","05:00 PM"],
            "Thursday":  ["09:00 AM","10:00 AM","02:00 PM","03:00 PM"],
            "Friday":    ["09:00 AM","11:00 AM","02:00 PM","04:00 PM"],
            "Saturday":  ["09:00 AM","10:00 AM","11:00 AM"],
            "Sunday":    [],
        },
    },
    "Dr. Arjun Sharma": {
        "specialty": "Dermatology", "department": "Dermatology",
        "qualification": "MBBS, DNB Dermatology", "experience": "8 years",
        "languages": ["English", "Hindi"], "fee": "₹400", "rating": 4.6,
        "slots": {
            "Monday":    ["10:00 AM","11:00 AM","12:00 PM","03:00 PM","05:00 PM","06:00 PM"],
            "Tuesday":   ["10:00 AM","12:00 PM","03:00 PM","05:00 PM","06:00 PM"],
            "Wednesday": ["11:00 AM","12:00 PM","04:00 PM","05:00 PM","06:00 PM"],
            "Thursday":  ["10:00 AM","11:00 AM","03:00 PM","05:00 PM","06:00 PM"],
            "Friday":    ["10:00 AM","12:00 PM","05:00 PM","06:00 PM"],
            "Saturday":  ["10:00 AM","11:00 AM","12:00 PM","01:00 PM"],
            "Sunday":    [],
        },
    },
    "Dr. Priya Nair": {
        "specialty": "Cardiology", "department": "Cardiology",
        "qualification": "MBBS, MD, DM Cardiology", "experience": "15 years",
        "languages": ["English", "Malayalam", "Tamil"], "fee": "₹800", "rating": 4.9,
        "slots": {
            "Monday":    ["08:00 AM","09:00 AM","10:00 AM","02:00 PM","03:00 PM"],
            "Tuesday":   ["08:00 AM","09:00 AM","02:00 PM","03:00 PM","04:00 PM"],
            "Wednesday": ["08:00 AM","10:00 AM","02:00 PM","04:00 PM"],
            "Thursday":  ["09:00 AM","10:00 AM","02:00 PM","03:00 PM","04:00 PM"],
            "Friday":    ["08:00 AM","09:00 AM","02:00 PM"],
            "Saturday":  ["09:00 AM","10:00 AM"],
            "Sunday":    [],
        },
    },
    "Dr. Venkat Rao": {
        "specialty": "Orthopedics", "department": "Orthopedics",
        "qualification": "MBBS, MS Orthopedics", "experience": "20 years",
        "languages": ["English", "Telugu"], "fee": "₹600", "rating": 4.7,
        "slots": {
            "Monday":    ["09:00 AM","10:00 AM","11:00 AM","03:00 PM","04:00 PM","05:00 PM"],
            "Tuesday":   ["09:00 AM","11:00 AM","03:00 PM","05:00 PM"],
            "Wednesday": ["10:00 AM","11:00 AM","12:00 PM","04:00 PM","05:00 PM"],
            "Thursday":  ["09:00 AM","10:00 AM","03:00 PM","04:00 PM","05:00 PM"],
            "Friday":    ["09:00 AM","11:00 AM","03:00 PM","05:00 PM"],
            "Saturday":  ["09:00 AM","10:00 AM","11:00 AM","12:00 PM"],
            "Sunday":    [],
        },
    },
    "Dr. Meena Krishnan": {
        "specialty": "Pediatrics", "department": "Pediatrics",
        "qualification": "MBBS, MD Pediatrics", "experience": "10 years",
        "languages": ["English", "Tamil", "Telugu"], "fee": "₹450", "rating": 4.8,
        "slots": {
            "Monday":    ["09:00 AM","10:00 AM","11:00 AM","12:00 PM","04:00 PM","05:00 PM"],
            "Tuesday":   ["09:00 AM","10:00 AM","11:00 AM","04:00 PM","05:00 PM"],
            "Wednesday": ["09:00 AM","11:00 AM","12:00 PM","04:00 PM","05:00 PM"],
            "Thursday":  ["09:00 AM","10:00 AM","11:00 AM","04:00 PM","05:00 PM"],
            "Friday":    ["09:00 AM","10:00 AM","04:00 PM","05:00 PM"],
            "Saturday":  ["09:00 AM","10:00 AM","11:00 AM","12:00 PM"],
            "Sunday":    ["10:00 AM","11:00 AM"],
        },
    },
    "Dr. Ravi Shankar": {
        "specialty": "General Medicine", "department": "General Medicine",
        "qualification": "MBBS, MD General Medicine", "experience": "18 years",
        "languages": ["English", "Hindi", "Telugu", "Kannada"], "fee": "₹350", "rating": 4.5,
        "slots": {
            "Monday":    ["08:00 AM","09:00 AM","10:00 AM","11:00 AM","02:00 PM","03:00 PM","04:00 PM","05:00 PM"],
            "Tuesday":   ["08:00 AM","09:00 AM","10:00 AM","02:00 PM","03:00 PM","04:00 PM","05:00 PM"],
            "Wednesday": ["08:00 AM","09:00 AM","11:00 AM","02:00 PM","04:00 PM","05:00 PM"],
            "Thursday":  ["08:00 AM","09:00 AM","10:00 AM","02:00 PM","03:00 PM","05:00 PM"],
            "Friday":    ["08:00 AM","09:00 AM","10:00 AM","02:00 PM","03:00 PM","04:00 PM"],
            "Saturday":  ["08:00 AM","09:00 AM","10:00 AM","11:00 AM","12:00 PM"],
            "Sunday":    ["09:00 AM","10:00 AM"],
        },
    },
    "Dr. Sunita Patel": {
        "specialty": "Gynecology", "department": "Gynecology & Obstetrics",
        "qualification": "MBBS, MS Gynecology", "experience": "14 years",
        "languages": ["English", "Hindi", "Gujarati"], "fee": "₹650", "rating": 4.9,
        "slots": {
            "Monday":    ["10:00 AM","11:00 AM","12:00 PM","03:00 PM","04:00 PM","05:00 PM"],
            "Tuesday":   ["10:00 AM","11:00 AM","03:00 PM","04:00 PM","05:00 PM"],
            "Wednesday": ["10:00 AM","12:00 PM","03:00 PM","05:00 PM"],
            "Thursday":  ["10:00 AM","11:00 AM","12:00 PM","03:00 PM","04:00 PM"],
            "Friday":    ["10:00 AM","11:00 AM","03:00 PM","04:00 PM"],
            "Saturday":  ["10:00 AM","11:00 AM","12:00 PM"],
            "Sunday":    [],
        },
    },
    "Dr. Anil Kumar": {
        "specialty": "Neurology", "department": "Neurology",
        "qualification": "MBBS, MD, DM Neurology", "experience": "16 years",
        "languages": ["English", "Hindi", "Telugu"], "fee": "₹900", "rating": 4.7,
        "slots": {
            "Monday":    ["09:00 AM","10:00 AM","02:00 PM","03:00 PM"],
            "Tuesday":   ["09:00 AM","11:00 AM","02:00 PM","04:00 PM"],
            "Wednesday": ["10:00 AM","11:00 AM","03:00 PM","04:00 PM"],
            "Thursday":  ["09:00 AM","10:00 AM","02:00 PM","03:00 PM"],
            "Friday":    ["09:00 AM","11:00 AM","02:00 PM"],
            "Saturday":  ["09:00 AM","10:00 AM"],
            "Sunday":    [],
        },
    },
}

APPOINTMENTS: dict = {}
REMINDERS: list = []


def _now_ist() -> datetime:
    return datetime.now(IST)

def _greeting() -> str:
    h = _now_ist().hour
    if h < 12: return "Good morning"
    if h < 17: return "Good afternoon"
    return "Good evening"

def _ist_now_str() -> str:
    return _now_ist().strftime("%I:%M %p, %A %B %d %Y (IST)")

def _ist_date_str() -> str:
    return _now_ist().strftime("%A, %B %d %Y")

def _today_ist_str() -> str:
    return _now_ist().strftime("%Y-%m-%d")

def _new_patient_id() -> str:
    pid = "PAT-" + str(random.randint(1000, 9999))
    while pid in APPOINTMENTS:
        pid = "PAT-" + str(random.randint(1000, 9999))
    return pid

def _resolve_doctor(name: str):
    for k in DOCTORS_DB:
        if name.lower() in k.lower() or k.lower() in name.lower():
            return k
    return None

def _parse_day(date_str: str) -> str:
    s = date_str.strip().lower()
    if "tomorrow" in s:
        return (_now_ist() + timedelta(days=1)).strftime("%A")
    if "today" in s:
        return _now_ist().strftime("%A")
    for fmt in ("%B %d, %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%A")
        except ValueError:
            continue
    return _now_ist().strftime("%A")

def _parse_date_to_ymd(date_str: str) -> str:
    s = date_str.strip().lower()
    if "today" in s:
        return _today_ist_str()
    if "tomorrow" in s:
        return (_now_ist() + timedelta(days=1)).strftime("%Y-%m-%d")
    for fmt in ("%B %d, %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""

def _slot_to_minutes(slot: str) -> int:
    try:
        dt = datetime.strptime(slot.strip(), "%I:%M %p")
        return dt.hour * 60 + dt.minute
    except ValueError:
        try:
            dt = datetime.strptime(slot.strip(), "%H:%M")
            return dt.hour * 60 + dt.minute
        except ValueError:
            return 0

def _is_slot_in_future(slot: str, date_ymd: str) -> bool:
    today_ymd = _today_ist_str()
    if date_ymd != today_ymd:
        return True
    now_ist   = _now_ist()
    now_mins  = now_ist.hour * 60 + now_ist.minute
    slot_mins = _slot_to_minutes(slot)
    return slot_mins > now_mins + 30


# ── Tools ──────────────────────────────────────────────────
def get_doctors_by_specialty(tool_context: ToolContext, specialty: str = None) -> dict:
    """Get list of doctors filtered by specialty. Shows name, qualification and fee only."""
    out = []
    for name, info in DOCTORS_DB.items():
        if specialty is None or specialty.lower() in info["specialty"].lower() \
                or specialty.lower() in info["department"].lower():
            out.append({
                "name":          name,
                "qualification": info["qualification"],
                "fee":           info["fee"],
            })
    if not out:
        return {
            "error": (
                f"No doctors for '{specialty}'. "
                "Available: Dermatology, Cardiology, Orthopedics, "
                "Pediatrics, General Medicine, Gynecology, Neurology"
            )
        }
    return {
        "doctors":              out,
        "count":                len(out),
        "auto_select":          len(out) == 1,
        "auto_selected_doctor": out[0]["name"] if len(out) == 1 else None,
    }


def get_doctor_slots(tool_context: ToolContext, doctor_name: str, date: str) -> dict:
    """Get available upcoming slots for a doctor on a date."""
    matched = _resolve_doctor(doctor_name)
    if not matched:
        return {"error": f"Doctor '{doctor_name}' not found."}
    info      = DOCTORS_DB[matched]
    day       = _parse_day(date)
    date_ymd  = _parse_date_to_ymd(date)
    all_slots = info["slots"].get(day, [])
    booked = [
        a["appointment_time"] for a in APPOINTMENTS.values()
        if a["doctor"] == matched
        and a["appointment_date"] == date
        and a["status"] != "cancelled"
    ]
    unbooked  = [s for s in all_slots if s not in booked]
    today_ymd = _today_ist_str()
    is_today  = (date_ymd == today_ymd) or ("today" in date.lower())
    available = [s for s in unbooked if _is_slot_in_future(s, today_ymd if is_today else "future")]
    past_removed = len(unbooked) - len(available)
    result = {
        "doctor":          matched,
        "specialty":       info["specialty"],
        "date":            date,
        "day":             day,
        "fee":             info["fee"],
        "available_slots": available,
        "booked_slots":    booked,
        "total_available": len(available),
    }
    if is_today and past_removed > 0:
        now_str = _now_ist().strftime("%I:%M %p")
        result["note"] = (
            f"{past_removed} earlier slot(s) removed — already past current IST time ({now_str}). "
            f"Showing only upcoming slots."
        )
    if not available:
        result["message"] = (
            f"No more slots available for today ({day}). "
            "Would you like to book for tomorrow or another day?"
        )
    return result


def book_appointment(tool_context: ToolContext, patient_name: str, doctor_name: str,
                     appointment_date: str, appointment_time: str,
                     purpose: str = "General consultation") -> dict:
    """Book appointment after doctor and slot confirmed."""
    matched = _resolve_doctor(doctor_name)
    if not matched:
        return {"error": f"Doctor '{doctor_name}' not found."}
    info = DOCTORS_DB[matched]
    date_ymd = _parse_date_to_ymd(appointment_date)
    if not _is_slot_in_future(appointment_time, date_ymd):
        return {"error": f"Slot {appointment_time} has already passed. Please choose an upcoming slot."}
    booked = [
        a["appointment_time"] for a in APPOINTMENTS.values()
        if a["doctor"] == matched
        and a["appointment_date"] == appointment_date
        and a["status"] != "cancelled"
    ]
    if appointment_time in booked:
        return {"error": f"Slot {appointment_time} already taken on {appointment_date}."}
    pid = _new_patient_id()
    APPOINTMENTS[pid] = {
        "patient_id":       pid,
        "patient_name":     patient_name,
        "doctor":           matched,
        "specialty":        info["specialty"],
        "department":       info["department"],
        "appointment_time": appointment_time,
        "appointment_date": appointment_date,
        "purpose":          purpose,
        "fee":              info["fee"],
        "status":           "confirmed",
        "booked_at":        _now_ist().isoformat(),
    }
    db_save_meeting(
        title=f"{patient_name} – {matched}",
        purpose=purpose,
        meeting_time=f"{appointment_date} {appointment_time}",
    )
    return {
        "message":          "Appointment confirmed!",
        "patient_id":       pid,
        "patient_name":     patient_name,
        "doctor":           matched,
        "specialty":        info["specialty"],
        "appointment_time": appointment_time,
        "appointment_date": appointment_date,
        "fee":              info["fee"],
        "purpose":          purpose,
        "post_booking_message": (
            "Please arrive 15 minutes early. "
            "Bring any previous medical reports, prescriptions, or test results."
        ),
    }


def get_appointment(tool_context: ToolContext, patient_id: str) -> dict:
    """Look up appointment by patient ID."""
    appt = APPOINTMENTS.get(patient_id.upper().strip())
    return appt if appt else {"error": f"No appointment found for Patient ID: {patient_id}."}


def reschedule_appointment(tool_context: ToolContext, patient_id: str,
                            new_date: str, new_time: str, reason: str = None) -> dict:
    """Reschedule an existing appointment."""
    appt = APPOINTMENTS.get(patient_id.upper().strip())
    if not appt: return {"error": f"No appointment for Patient ID: {patient_id}."}
    if appt["status"] == "cancelled": return {"error": "Appointment already cancelled."}
    date_ymd = _parse_date_to_ymd(new_date)
    if not _is_slot_in_future(new_time, date_ymd):
        return {"error": f"Slot {new_time} has already passed. Please choose an upcoming slot."}
    booked = [
        a["appointment_time"] for a in APPOINTMENTS.values()
        if a["doctor"] == appt["doctor"]
        and a["appointment_date"] == new_date
        and a["patient_id"] != patient_id
        and a["status"] != "cancelled"
    ]
    if new_time in booked: return {"error": f"Slot {new_time} is taken on {new_date}."}
    old_d, old_t = appt["appointment_date"], appt["appointment_time"]
    appt.update({
        "appointment_date":  new_date,
        "appointment_time":  new_time,
        "status":            "rescheduled",
        "reschedule_reason": reason or "Patient request",
    })
    return {
        "message":    f"Appointment {patient_id} rescheduled.",
        "patient_id": patient_id,
        "doctor":     appt["doctor"],
        "old_date":   old_d, "old_time": old_t,
        "new_date":   new_date, "new_time": new_time,
        "post_booking_message": (
            "Please arrive 15 minutes early. "
            "Bring any previous medical reports, prescriptions, or test results."
        ),
    }


def cancel_appointment(tool_context: ToolContext, patient_id: str, reason: str = None) -> dict:
    """Cancel an appointment by patient ID."""
    appt = APPOINTMENTS.get(patient_id.upper().strip())
    if not appt: return {"error": f"No appointment for Patient ID: {patient_id}."}
    if appt["status"] == "cancelled": return {"error": "Already cancelled."}
    appt.update({"status": "cancelled", "cancel_reason": reason or "Patient request"})
    return {
        "message":      f"Appointment {patient_id} cancelled.",
        "patient_id":   patient_id,
        "patient_name": appt["patient_name"],
        "doctor":       appt["doctor"],
        "status":       "cancelled",
    }


def list_appointments(tool_context: ToolContext) -> dict:
    """List all appointments."""
    if not APPOINTMENTS: return {"message": "No appointments on record."}
    return {
        "confirmed":   [a for a in APPOINTMENTS.values() if a["status"] == "confirmed"],
        "rescheduled": [a for a in APPOINTMENTS.values() if a["status"] == "rescheduled"],
        "cancelled":   [a for a in APPOINTMENTS.values() if a["status"] == "cancelled"],
        "total":       len(APPOINTMENTS),
    }


# ── Reminder Tools ─────────────────────────────────────────
def set_reminder(tool_context: ToolContext, patient_id: str, patient_name: str,
                 doctor_name: str, appointment_date: str, appointment_time: str,
                 reminder_minutes: int = 30) -> dict:
    """Set a reminder for an appointment."""
    rid = "REM-" + str(random.randint(1000, 9999))
    REMINDERS.append({
        "reminder_id":           rid,
        "patient_id":            patient_id,
        "patient_name":          patient_name,
        "doctor":                doctor_name,
        "appointment_date":      appointment_date,
        "appointment_time":      appointment_time,
        "remind_before_minutes": reminder_minutes,
        "status":                "scheduled",
        "created_at":            _now_ist().isoformat(),
    })
    db_add_task(
        task=(
            f"🔔 REMINDER: {patient_name} — {doctor_name} on "
            f"{appointment_date} at {appointment_time} (alert {reminder_minutes} mins before)"
        ),
        priority="normal",
    )
    return {
        "message":      "✅ Reminder set!",
        "patient_name": patient_name,
        "doctor":       doctor_name,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "will_remind_at": f"{reminder_minutes} minutes before {appointment_time}",
    }


def get_reminders(tool_context: ToolContext, patient_id: str = None) -> dict:
    """Get all reminders."""
    if not REMINDERS: return {"message": "No reminders set."}
    filtered = [r for r in REMINDERS if not patient_id or r["patient_id"] == patient_id.upper()]
    return {"reminders": filtered, "total": len(filtered)} if filtered else \
           {"message": f"No reminders found for Patient ID: {patient_id}"}


def cancel_reminder(tool_context: ToolContext, reminder_id: str) -> dict:
    """Cancel a reminder."""
    for r in REMINDERS:
        if r["reminder_id"] == reminder_id.upper():
            r["status"] = "cancelled"
            return {"message": f"Reminder {reminder_id} cancelled."}
    return {"error": f"Reminder {reminder_id} not found."}


# ── MCP disabled for Cloud Run ─────────────────────────────
print("ℹ️  Running in direct mode")
_appt_tools = [
    get_doctors_by_specialty, get_doctor_slots, book_appointment,
    get_appointment, reschedule_appointment, cancel_appointment, list_appointments,
]

_now  = _ist_now_str()
_date = _ist_date_str()

# ── Agents ─────────────────────────────────────────────────
appointment_agent = Agent(
    name="appointment_agent",
    model=model_name,
    description="Handles all appointment booking, rescheduling and cancellation",
    instruction=f"""You are the Appointment module of NEXA Hospital Assistant.
Current time (IST): {_now}

TOOLS:
- get_doctors_by_specialty → list doctors for a specialty
- get_doctor_slots         → available upcoming slots for a doctor on a date
- book_appointment         → confirm booking
- get_appointment          → lookup by Patient ID
- reschedule_appointment   → change schedule
- cancel_appointment       → cancel
- list_appointments        → all appointments

DOCTOR LISTING FORMAT — always show exactly like this, no extra info:
"We have X doctor(s) available for [specialty]:
1. Dr. Name — [qualification] | Consultation Fee: ₹XXX
2. Dr. Name — [qualification] | Consultation Fee: ₹XXX
Which doctor would you like?"

SLOT DISPLAY:
- Show only available_slots from get_doctor_slots
- If result has "note" field, always show it to patient
- If no slots today, suggest tomorrow

BOOKING FLOW:
1. Specialty/concern → call get_doctors_by_specialty → show in above format
2. auto_select=true → say "Found [doctor]! Checking slots..." → call get_doctor_slots immediately
3. auto_select=false → show list → patient picks
4. Call get_doctor_slots → show slots
5. Patient picks slot → confirm details → call book_appointment
6. Show confirmation with PAT-XXXX and ALWAYS end with:
   "📋 Please remember to:
   • Arrive 15 minutes early
   • Bring any previous medical reports, prescriptions, or test results"
7. Say "🔔 Setting your reminder now!" → transfer to reminder_agent

RESCHEDULE/CANCEL: Ask Patient ID → verify → confirm → execute.
Be professional and compassionate.""",
    tools=_appt_tools,
)

reminder_agent = Agent(
    name="reminder_agent",
    model=model_name,
    description="Sets and manages appointment reminders",
    instruction="""You are the Reminder module of NEXA Hospital Assistant.

TOOLS:
- set_reminder:    Set reminder (default 30 min before).
- get_reminders:   List reminders for a patient.
- cancel_reminder: Cancel by reminder ID.

After booking, auto-call set_reminder with patient details.
Confirm warmly: "🔔 Done! I've set a reminder 30 minutes before your appointment. You're all set!"
Adjust if patient wants different lead time.""",
    tools=[set_reminder, get_reminders, cancel_reminder],
)

root_agent = Agent(
    name="productivity_root",
    model=model_name,
    description="NEXA — Hospital Appointment Assistant",
    instruction=f"""You are NEXA — Hospital Appointment Assistant. Today is {_date} (IST).

ON FIRST MESSAGE greet exactly:
---
{_greeting()}! I'm NEXA, your Hospital Appointment Assistant. 🏥

I can help you with:
📅 Book an appointment with a doctor
🔄 Reschedule or cancel an existing appointment
🩺 Check doctor availability

To reschedule or cancel, you'll need your 🪪 Patient ID (given at booking).
How can I assist you today?
---

ROUTING:
- book / appointment / doctor / specialty / pain / concern → appointment_agent
- reschedule / change / move appointment                  → appointment_agent
- cancel appointment                                      → appointment_agent
- my appointment / patient id / lookup                    → appointment_agent
- reminder / remind me                                    → reminder_agent

After every booking, reminder_agent auto-sets a 30-min reminder.""",
    tools=[list_appointments],
    sub_agents=[appointment_agent, reminder_agent],
)

agent = root_agent