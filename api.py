"""
FastAPI server — exposes the productivity agent as a REST API.
Local:      uvicorn api:app --reload --port 8080
Cloud Run:  bash deploy.sh
Docs:       http://localhost:8080/docs
"""
import os
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

from database import (
    init_db, db_get_tasks, db_get_notes, db_get_meetings,
    db_add_task, db_save_note, db_save_meeting,
    db_complete_task, db_delete_task
)

# ── Globals ───────────────────────────────────────────────
_runner = None
_session_id = None
_session_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("✅ Database initialized")
    yield

app = FastAPI(
    title="🤖 Multi-Agent Productivity Assistant",
    description="""
## AI-powered productivity API

Built with **Google ADK**, **Gemini**, **MCP tools** (Google Calendar + Gmail), and **SQLite**.

### Features
- 🤖 Multi-agent AI chat (tasks, notes, calendar, email)
- 📋 Task management with priority & due dates
- 📝 Note-taking with search
- 📅 Google Calendar integration via MCP
- 📧 Gmail integration — send email summaries
- ⏰ Smart reminders
- 📊 Productivity dashboard
    """,
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Lazy ADK runner ───────────────────────────────────────
async def get_runner():
    global _runner, _session_id, _session_service
    if _runner is None:
        from agent import root_agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        _session_service = InMemorySessionService()
        _runner = Runner(agent=root_agent, app_name="productivity", session_service=_session_service)
        sess = await _session_service.create_session(app_name="productivity", user_id="api_user")
        _session_id = sess.id
        print("✅ ADK Runner initialized")
    return _runner

# ═══════════════════════════════════════════════════════════
# 🏠  Root — web UI
# ═══════════════════════════════════════════════════════════
@app.get("/", response_class=HTMLResponse)
def root():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Productivity Agent</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 2rem; }
  h1 { font-size: 2rem; margin-bottom: 0.5rem; background: linear-gradient(135deg, #6366f1, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .subtitle { color: #94a3b8; margin-bottom: 2rem; text-align: center; }
  .chat-box { width: 100%; max-width: 700px; background: #1e293b; border-radius: 16px; padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
  #messages { min-height: 300px; max-height: 500px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.75rem; }
  .msg { padding: 0.75rem 1rem; border-radius: 12px; max-width: 85%; line-height: 1.5; white-space: pre-wrap; }
  .user { background: #4f46e5; align-self: flex-end; }
  .agent { background: #334155; align-self: flex-start; }
  .input-row { display: flex; gap: 0.5rem; }
  input { flex: 1; padding: 0.75rem 1rem; border-radius: 10px; border: 1px solid #334155; background: #0f172a; color: #e2e8f0; font-size: 1rem; }
  button { padding: 0.75rem 1.5rem; border-radius: 10px; border: none; background: #4f46e5; color: white; font-size: 1rem; cursor: pointer; }
  button:hover { background: #6366f1; }
  .chips { display: flex; gap: 0.5rem; flex-wrap: wrap; }
  .chip { padding: 0.4rem 0.9rem; border-radius: 999px; background: #1e3a5f; color: #93c5fd; font-size: 0.8rem; cursor: pointer; border: 1px solid #2563eb40; }
  .chip:hover { background: #2563eb; color: white; }
  .links { margin-top: 1.5rem; display: flex; gap: 1rem; }
  a { color: #818cf8; text-decoration: none; font-size: 0.9rem; }
  a:hover { color: #a5b4fc; }
</style>
</head>
<body>
<h1>🤖 Productivity Agent</h1>
<p class="subtitle">Your AI assistant for tasks, notes, calendar & email</p>
<div class="chat-box">
  <div id="messages">
    <div class="msg agent">👋 Hello! I'm your AI productivity assistant. I can help you manage tasks, take notes, check your calendar, and send email summaries. What would you like to do?</div>
  </div>
  <div class="chips">
    <span class="chip" onclick="send('Show my dashboard')">📊 Dashboard</span>
    <span class="chip" onclick="send('Show pending tasks')">📋 Tasks</span>
    <span class="chip" onclick="send('Show my notes')">📝 Notes</span>
    <span class="chip" onclick="send('Show upcoming meetings')">📅 Calendar</span>
    <span class="chip" onclick="send('Send me an email summary')">📧 Email summary</span>
  </div>
  <div class="input-row">
    <input id="inp" placeholder="Type a message..." onkeydown="if(event.key==='Enter') send()"/>
    <button onclick="send()">Send</button>
  </div>
</div>
<div class="links">
  <a href="/docs" target="_blank">📖 API Docs</a>
  <a href="/dashboard" target="_blank">📊 Dashboard JSON</a>
  <a href="/tasks" target="_blank">📋 Tasks JSON</a>
</div>
<script>
async function send(text) {
  const inp = document.getElementById('inp');
  const msgs = document.getElementById('messages');
  const msg = text || inp.value.trim();
  if (!msg) return;
  inp.value = '';
  msgs.innerHTML += `<div class="msg user">${msg}</div>`;
  msgs.scrollTop = msgs.scrollHeight;
  const thinking = document.createElement('div');
  thinking.className = 'msg agent';
  thinking.textContent = '⏳ Thinking...';
  msgs.appendChild(thinking);
  msgs.scrollTop = msgs.scrollHeight;
  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg})
    });
    const data = await res.json();
    thinking.textContent = data.response || data.detail || 'Error';
  } catch(e) {
    thinking.textContent = '⚠️ Connection error';
  }
  msgs.scrollTop = msgs.scrollHeight;
}
</script>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════════
# 💬  Chat
# ═══════════════════════════════════════════════════════════
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(req: ChatRequest):
    """Send a message to the AI productivity agent."""
    try:
        from google.genai import types
        r = await get_runner()
        content = types.Content(role="user", parts=[types.Part(text=req.message)])
        reply = ""
        async for event in r.run_async(user_id="api_user", session_id=_session_id, new_message=content):
            if event.is_final_response() and event.content and event.content.parts:
                reply = event.content.parts[0].text
        return ChatResponse(response=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════
# 📋  Tasks
# ═══════════════════════════════════════════════════════════
class TaskCreate(BaseModel):
    task: str
    priority: str = "normal"
    due_date: str = None

@app.get("/tasks", tags=["Tasks"])
def list_tasks(status: str = None):
    """List all tasks. Filter: ?status=pending or ?status=done"""
    return {"tasks": db_get_tasks(status)}

@app.post("/tasks", tags=["Tasks"])
def create_task(body: TaskCreate):
    """Create a new task."""
    return db_add_task(body.task, body.priority, body.due_date)

@app.patch("/tasks/{task_id}/complete", tags=["Tasks"])
def complete_task_api(task_id: int):
    """Mark a task as completed."""
    return db_complete_task(task_id)

@app.delete("/tasks/{task_id}", tags=["Tasks"])
def delete_task_api(task_id: int):
    """Delete a task."""
    return db_delete_task(task_id)

# ═══════════════════════════════════════════════════════════
# 📝  Notes
# ═══════════════════════════════════════════════════════════
class NoteCreate(BaseModel):
    content: str
    title: str = None
    tags: str = None

@app.get("/notes", tags=["Notes"])
def list_notes(search: str = None):
    """List all notes. Search: ?search=keyword"""
    return {"notes": db_get_notes(search)}

@app.post("/notes", tags=["Notes"])
def create_note(body: NoteCreate):
    """Save a new note."""
    return db_save_note(body.content, body.title, body.tags)

# ═══════════════════════════════════════════════════════════
# 📅  Meetings
# ═══════════════════════════════════════════════════════════
class MeetingCreate(BaseModel):
    title: str
    purpose: str = None
    meeting_time: str = None
    participants: str = None

@app.get("/meetings", tags=["Meetings"])
def list_meetings():
    """List all scheduled meetings."""
    return {"meetings": db_get_meetings()}

@app.post("/meetings", tags=["Meetings"])
def create_meeting(body: MeetingCreate):
    """Schedule a new meeting."""
    return db_save_meeting(body.title, body.purpose, body.meeting_time, body.participants)

# ═══════════════════════════════════════════════════════════
# 📊  Dashboard
# ═══════════════════════════════════════════════════════════
@app.get("/dashboard", tags=["Dashboard"])
def dashboard():
    """Full productivity dashboard — summary of all data."""
    tasks = db_get_tasks()
    pending = [t for t in tasks if t["status"] == "pending"]
    done = [t for t in tasks if t["status"] == "done"]
    high_priority = [t for t in pending if t["priority"] == "high"]
    notes = db_get_notes()
    meetings = db_get_meetings()
    return {
        "summary": {
            "total_tasks": len(tasks),
            "pending_tasks": len(pending),
            "completed_tasks": len(done),
            "high_priority_tasks": len(high_priority),
            "total_notes": len(notes),
            "total_meetings": len(meetings),
            "completion_rate": f"{round(len(done)/len(tasks)*100)}%" if tasks else "0%"
        },
        "high_priority": high_priority,
        "upcoming_meetings": meetings[:5],
        "recent_notes": notes[:3]
    }

@app.get("/health", tags=["System"])
def health():
    return {"status": "healthy", "version": "2.0.0", "model": os.getenv("MODEL", "gemini-2.0-flash")}
