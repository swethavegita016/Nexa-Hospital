"""
api.py — NEXA Hospital Appointment Assistant
FastAPI server for Cloud Run deployment
"""
import os, sys, uuid, json
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, os.path.dirname(__file__))

try:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types
    from agent import root_agent, DOCTORS_DB, APPOINTMENTS
    ADK_AVAILABLE = True
    print("✅ ADK + agent.py loaded")
except Exception as e:
    ADK_AVAILABLE = False
    DOCTORS_DB = {}
    APPOINTMENTS = {}
    print(f"⚠️  ADK import failed: {e}")

sessions, runners = {}, {}
session_service = InMemorySessionService() if ADK_AVAILABLE else None
APP_NAME, USER_ID = "nexa_hospital", "user"

async def get_or_create_session(sid: str):
    if sid not in sessions:
        if ADK_AVAILABLE:
            sessions[sid] = await session_service.create_session(
                app_name=APP_NAME, user_id=USER_ID, session_id=sid)
            runners[sid] = Runner(
                agent=root_agent, app_name=APP_NAME, session_service=session_service)
        else:
            sessions[sid] = {"id": sid}
            runners[sid] = None
    return sessions[sid], runners.get(sid)

async def call_agent(sid: str, msg: str):
    _, runner = await get_or_create_session(sid)
    if not ADK_AVAILABLE or not runner:
        yield f"data: {json.dumps({'type':'token','text':f'[DEMO] {msg}'})}\n\n"
        yield f"data: {json.dumps({'type':'done'})}\n\n"
        return
    content = genai_types.Content(role="user", parts=[genai_types.Part(text=msg)])
    try:
        async for event in runner.run_async(user_id=USER_ID, session_id=sid, new_message=content):
            agent_name = getattr(event, 'author', 'nexa_root') or 'nexa_root'
            if hasattr(event, 'get_function_calls') and event.get_function_calls():
                for fc in event.get_function_calls():
                    yield f"data: {json.dumps({'type':'tool_call','tool':fc.name})}\n\n"
            if hasattr(event, 'get_function_responses') and event.get_function_responses():
                for fr in event.get_function_responses():
                    yield f"data: {json.dumps({'type':'tool_result','tool':fr.name})}\n\n"
            if hasattr(event, 'content') and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        yield f"data: {json.dumps({'type':'token','text':part.text,'agent':agent_name})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type':'error','text':str(e)})}\n\n"
    yield f"data: {json.dumps({'type':'done'})}\n\n"

# Import HTML from chat_ui
from chat_ui import HTML

app = FastAPI(title="NEXA Hospital Appointment Assistant")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    sid  = body.get("session_id", str(uuid.uuid4()))
    msg  = body.get("message", "").strip()
    if not msg:
        return JSONResponse({"error": "empty"}, status_code=400)
    return StreamingResponse(
        call_agent(sid, msg),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.get("/health")
async def health():
    return {"status": "ok", "adk": ADK_AVAILABLE}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")