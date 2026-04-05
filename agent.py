"""
agent.py — NEXA Hospital Appointment Assistant with Reminder Agent
MCP disabled for Cloud Run compatibility (stdio not supported in containers)
"""

import os, sys, random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

sys.path.insert(0, os.path.dirname(__file__))
from database import init_db, db_save_meeting, db_add_task, db_get_tasks

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
model_name = os.getenv("MODEL", "gemini-2.0-flash")
init_db()

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


# ── Helpers ────────────────────────────────────────────────────────────────
def _greeting():
    h = datetime.now().hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"

def _new_patient_id():
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
        return (datetime.now() + timedelta(days=1)).strftime("%A")
    if "today" in s:
        return datetime.now().strftime("%A")
    for fmt in ("%B %d, %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%A")
        except ValueError:
            continue
    return datetime.now().strftime("%A")


# ── Appointment Tools ──────────────────────────────────────────────────────
def get_doctors_by_specialty(tool_context: ToolContext, specialty: str = None) -> dict:
    """Get list of doctors filtered by specialty."""
    out = []
    for name, info in DOCTORS_DB.items():
        if specialty is None or specialty.lower() in info["specialty"].lower() \
                or specialty.lower() in info["department"].lower():
            out.append({
                "name": name,
                "specialty": info["specialty"],
                "qualification": info["qualification"],
            })
    if not out:
        return {
            "error": f"No doctors for '{specialty}'. "
                     "Available: Dermatology, Cardiology, Orthopedics, Pediatrics, "
                     "General Medicine, Gynecology, Neurology"
        }
    return {"doctors": out, "count": len(out)}


def get_doctor_slots(tool_context: ToolContext, doctor_name: str, date: str) -> dict:
    """Get available slots for a doctor on a date."""
    matched = _resolve_doctor(doctor_name)
    if not matched:
        return {"error": f"Doctor '{doctor_name}' not found."}
    info = DOCTORS_DB[matched]
    day  = _parse_day(date)
    all_slots = info["slots"].get(day, [])
    booked = [
        a["appointment_time"] for a in APPOINTMENTS.values()
        if a["doctor"] == matched and a["appointment_date"] == date
        and a["status"] != "cancelled"
    ]
    available = [s for s in all_slots if s not in booked]
    return {
        "doctor": matched, "specialty": info["specialty"],
        "date": date, "day": day, "fee": info["fee"],
        "available_slots": available, "booked_slots": booked,
    }


def book_appointment(tool_context: ToolContext, patient_name: str, doctor_name: str,
                     appointment_date: str, appointment_time: str,
                     purpose: str = "General consultation") -> dict:
    """Book appointment after doctor and slot selected."""
    matched = _resolve_doctor(doctor_name)
    if not matched:
        return {"error": f"Doctor '{doctor_name}' not found."}
    info = DOCTORS_DB[matched]
    booked = [
        a["appointment_time"] for a in APPOINTMENTS.values()
        if a["doctor"] == matched and a["appointment_date"] == appointment_date
        and a["status"] != "cancelled"
    ]
    if appointment_time in booked:
        return {"error": f"Slot {appointment_time} already taken on {appointment_date}."}
    pid = _new_patient_id()
    APPOINTMENTS[pid] = {
        "patient_id": pid, "patient_name": patient_name,
        "doctor": matched, "specialty": info["specialty"],
        "department": info["department"],
        "appointment_time": appointment_time, "appointment_date": appointment_date,
        "purpose": purpose, "fee": info["fee"], "status": "confirmed",
        "booked_at": datetime.now().isoformat(),
    }
    db_save_meeting(
        title=f"{patient_name} – {matched}", purpose=purpose,
        meeting_time=f"{appointment_date} {appointment_time}",
    )
    return {
        "message": "Appointment confirmed!",
        "patient_id": pid, "patient_name": patient_name,
        "doctor": matched, "specialty": info["specialty"],
        "appointment_time": appointment_time, "appointment_date": appointment_date,
        "fee": info["fee"], "purpose": purpose,
        "instructions": "Please arrive 15 minutes early and bring previous reports.",
        "reminder_note": (
            f"A reminder will be set 30 minutes before your appointment "
            f"at {appointment_time} on {appointment_date}."
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
    if not appt:
        return {"error": f"No appointment for Patient ID: {patient_id}."}
    if appt["status"] == "cancelled":
        return {"error": "Appointment already cancelled."}
    booked = [
        a["appointment_time"] for a in APPOINTMENTS.values()
        if a["doctor"] == appt["doctor"] and a["appointment_date"] == new_date
        and a["patient_id"] != patient_id and a["status"] != "cancelled"
    ]
    if new_time in booked:
        return {"error": f"Slot {new_time} is taken on {new_date}."}
    old_d, old_t = appt["appointment_date"], appt["appointment_time"]
    appt.update({
        "appointment_date": new_date, "appointment_time": new_time,
        "status": "rescheduled", "reschedule_reason": reason or "Patient request",
    })
    return {
        "message": f"Appointment {patient_id} rescheduled.",
        "patient_id": patient_id, "doctor": appt["doctor"],
        "old_date": old_d, "old_time": old_t,
        "new_date": new_date, "new_time": new_time,
        "reminder_note": f"Reminder updated to 30 minutes before {new_time} on {new_date}.",
    }


def cancel_appointment(tool_context: ToolContext, patient_id: str, reason: str = None) -> dict:
    """Cancel an appointment by patient ID."""
    appt = APPOINTMENTS.get(patient_id.upper().strip())
    if not appt:
        return {"error": f"No appointment for Patient ID: {patient_id}."}
    if appt["status"] == "cancelled":
        return {"error": "Already cancelled."}
    appt.update({"status": "cancelled", "cancel_reason": reason or "Patient request"})
    return {
        "message": f"Appointment {patient_id} cancelled.",
        "patient_id": patient_id, "patient_name": appt["patient_name"],
        "doctor": appt["doctor"], "status": "cancelled",
    }


def list_appointments(tool_context: ToolContext) -> dict:
    """List all appointments."""
    if not APPOINTMENTS:
        return {"message": "No appointments on record."}
    return {
        "confirmed":   [a for a in APPOINTMENTS.values() if a["status"] == "confirmed"],
        "rescheduled": [a for a in APPOINTMENTS.values() if a["status"] == "rescheduled"],
        "cancelled":   [a for a in APPOINTMENTS.values() if a["status"] == "cancelled"],
        "total": len(APPOINTMENTS),
    }


# ── Reminder Tools ─────────────────────────────────────────────────────────
def set_reminder(tool_context: ToolContext, patient_id: str, patient_name: str,
                 doctor_name: str, appointment_date: str, appointment_time: str,
                 reminder_minutes: int = 30) -> dict:
    """Set a reminder for an appointment."""
    rid = "REM-" + str(random.randint(1000, 9999))
    reminder = {
        "reminder_id": rid,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "doctor": doctor_name,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "remind_before_minutes": reminder_minutes,
        "message": (
            f"Reminder: Your appointment with {doctor_name} is in "
            f"{reminder_minutes} minutes on {appointment_date} at {appointment_time}."
        ),
        "status": "scheduled",
        "created_at": datetime.now().isoformat(),
    }
    REMINDERS.append(reminder)
    db_add_task(
        task=(
            f"🔔 REMINDER [{rid}]: {patient_name} — {doctor_name} on "
            f"{appointment_date} at {appointment_time} (alert {reminder_minutes} mins before)"
        ),
        priority="normal",
    )
    return {
        "message": "✅ Reminder set!",
        "reminder_id": rid,
        "patient_name": patient_name,
        "doctor": doctor_name,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "will_remind_at": f"{reminder_minutes} minutes before {appointment_time}",
        "note": f"You will be notified {reminder_minutes} minutes before your appointment.",
    }


def get_reminders(tool_context: ToolContext, patient_id: str = None) -> dict:
    """Get all reminders, optionally filtered by patient ID."""
    if not REMINDERS:
        return {"message": "No reminders set."}
    filtered = [r for r in REMINDERS if not patient_id or r["patient_id"] == patient_id.upper()]
    if not filtered:
        return {"message": f"No reminders found for Patient ID: {patient_id}"}
    return {"reminders": filtered, "total": len(filtered)}


def cancel_reminder(tool_context: ToolContext, reminder_id: str) -> dict:
    """Cancel a reminder by reminder ID."""
    for r in REMINDERS:
        if r["reminder_id"] == reminder_id.upper():
            r["status"] = "cancelled"
            return {"message": f"Reminder {reminder_id} cancelled.", "reminder_id": reminder_id}
    return {"error": f"Reminder {reminder_id} not found."}


# ── MCP disabled for Cloud Run ─────────────────────────────────────────────
# stdio-based MCP subprocesses cannot run in containerised Cloud Run instances.
# All core features (booking, rescheduling, cancellation, reminders) work without MCP.
print("ℹ️  MCP disabled — running in Cloud Run mode (stdio subprocesses not supported)")
_appt_tools = [
    get_doctors_by_specialty,
    get_doctor_slots,
    book_appointment,
    get_appointment,
    reschedule_appointment,
    cancel_appointment,
    list_appointments,
]


_now  = datetime.now().strftime("%I:%M %p, %A %B %d %Y")
_date = datetime.now().strftime("%A, %B %d %Y")


# ── Sub-agents ─────────────────────────────────────────────────────────────
appointment_agent = Agent(
    name="appointment_agent",
    model=model_name,
    description="Handles all appointment booking, rescheduling and cancellation",
    instruction=f"""You are the Appointment module of NEXA Hospital Assistant.
Current time: {_now}

TOOLS:
- get_doctors_by_specialty → list doctors for a specialty
- get_doctor_slots         → available slots for a doctor on a date
- book_appointment         → confirm booking
- get_appointment          → lookup by Patient ID
- reschedule_appointment   → change schedule
- cancel_appointment       → cancel
- list_appointments        → all appointments

WHEN listing doctors, show ONLY their names in a simple numbered list:
"We have X doctors available for [specialty]:
1. Dr. Name
2. Dr. Name
Which doctor would you like?"

DO NOT show fee, rating, experience or qualifications unless patient explicitly asks.

BOOKING FLOW:
1. Specialty/concern mentioned → call get_doctors_by_specialty → show names only
2. Doctor selected → call get_doctor_slots for their date
3. Slot selected → confirm details → call book_appointment
4. Show PAT-XXXX prominently: "🪪 Patient ID: PAT-XXXX — please save this!"
5. After confirming booking, ALWAYS say:
   "🔔 I'll also set a reminder 30 minutes before your appointment so you don't miss it!"
   Then transfer to reminder_agent to set the reminder automatically.

RESCHEDULE/CANCEL: Ask for Patient ID → verify with get_appointment → confirm → execute.
Be calm, professional, and compassionate.""",
    tools=_appt_tools,
)

reminder_agent = Agent(
    name="reminder_agent",
    model=model_name,
    description="Sets and manages appointment reminders",
    instruction="""You are the Reminder module of NEXA Hospital Assistant.

TOOLS:
- set_reminder:    Set a reminder for an appointment. Default is 30 minutes before.
- get_reminders:   View all reminders for a patient.
- cancel_reminder: Cancel a reminder by reminder ID.

AFTER booking is confirmed, automatically call set_reminder using the patient
details passed from appointment_agent (patient_id, patient_name, doctor_name,
appointment_date, appointment_time). Use reminder_minutes=30 by default.

Always confirm with:
"🔔 Done! I've set a reminder for 30 minutes before your appointment. You're all set!"

If the patient wants a different lead time (e.g. 1 hour before), adjust reminder_minutes
accordingly and confirm the updated time.

Be warm and reassuring.""",
    tools=[set_reminder, get_reminders, cancel_reminder],
)

# ── Root agent ─────────────────────────────────────────────────────────────
root_agent = Agent(
    name="productivity_root",
    model=model_name,
    description="NEXA — Hospital Appointment Assistant",
    instruction=f"""You are NEXA — Hospital Appointment Assistant. Today is {_date}.

ON FIRST MESSAGE always greet exactly like this:
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
- book / appointment / doctor / specialty / available → appointment_agent
- reschedule / change / move appointment             → appointment_agent
- cancel appointment                                 → appointment_agent
- my appointment / patient id / lookup               → appointment_agent
- reminder / remind me / set reminder                → reminder_agent
- view reminders / my reminders                      → reminder_agent
- emergency → "Please call 108 or go to the Emergency Department immediately. 🚨"

After every successful booking, reminder_agent automatically sets a 30-min reminder.
Be calm, professional, and compassionate.""",
    tools=[list_appointments],
    sub_agents=[appointment_agent, reminder_agent],
)

agent = root_agent