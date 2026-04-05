"""
chat_ui.py — NEXA Hospital Appointment Assistant
Interactive doctor cards + time slot picker
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
            sessions[sid] = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=sid)
            runners[sid]  = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
        else:
            sessions[sid] = {"id": sid}
            runners[sid]  = None
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
            agent_name = getattr(event, 'author', 'productivity_root') or 'productivity_root'
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
            if hasattr(event, 'actions') and event.actions:
                if getattr(event.actions, 'transfer_to_agent', None):
                    yield f"data: {json.dumps({'type':'transfer','to':event.actions.transfer_to_agent})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type':'error','text':str(e)})}\n\n"
    yield f"data: {json.dumps({'type':'done'})}\n\n"


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>NEXA — Hospital Appointment Assistant</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@500;700;800&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#eef2f7;--surface:#fff;--panel:#f7f9fc;--border:#e2e8f0;--border-s:#cbd5e1;
  --blue:#2563eb;--blue-l:#dbeafe;--blue-m:#bfdbfe;--blue-d:#eff6ff;
  --green:#16a34a;--green-l:#dcfce7;--red:#dc2626;--orange:#ea580c;
  --text:#0f172a;--t2:#334155;--t3:#64748b;--t4:#94a3b8;
  --font:'Inter',sans-serif;--fh:'Outfit',sans-serif;
  --sh:0 1px 3px rgba(0,0,0,.08),0 4px 16px rgba(0,0,0,.05);
  --sh-s:0 1px 2px rgba(0,0,0,.06);
}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:var(--font);font-size:14px;overflow:hidden}
.app{display:grid;grid-template-rows:64px 1fr 72px;height:100vh}
header{background:var(--surface);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 24px;gap:14px;box-shadow:var(--sh-s);z-index:20}
.logo-mark{width:38px;height:38px;background:var(--blue);border-radius:10px;display:flex;align-items:center;justify-content:center;font-family:var(--fh);font-weight:800;font-size:15px;color:#fff;flex-shrink:0}
.logo-text{font-family:var(--fh);font-weight:700;font-size:18px;letter-spacing:-.3px}
.logo-sub{font-size:11px;color:var(--t3);letter-spacing:.4px;text-transform:uppercase;font-weight:500}
.hright{margin-left:auto;display:flex;align-items:center;gap:12px}
.pill{display:flex;align-items:center;gap:6px;padding:5px 13px;border-radius:20px;border:1px solid var(--border);background:var(--panel);font-size:12px;color:var(--t3);font-weight:500}
.dot-live{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 0 2px rgba(22,163,74,.2);animation:pulse 2.5s ease infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 2px rgba(22,163,74,.2)}50%{box-shadow:0 0 0 5px rgba(22,163,74,.04)}}
.nsb{height:32px;padding:0 14px;border-radius:7px;border:1px solid var(--border-s);background:var(--surface);color:var(--t2);font-size:12.5px;font-weight:500;cursor:pointer;font-family:var(--font);transition:all .15s}
.nsb:hover{background:var(--blue);color:#fff;border-color:var(--blue)}
.messages{overflow-y:auto;padding:20px 20px 8px;display:flex;flex-direction:column;gap:6px;scroll-behavior:smooth}
.messages::-webkit-scrollbar{width:5px}
.messages::-webkit-scrollbar-thumb{background:var(--border-s);border-radius:3px}
.msg{display:flex;gap:10px;padding:1px 0}
.msg.user{flex-direction:row-reverse}
.av{width:32px;height:32px;border-radius:9px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;font-family:var(--fh)}
.av.nx{background:var(--blue);color:#fff}
.av.us{background:#e2e8f0;color:var(--t3);font-size:15px}
.mbody{display:flex;flex-direction:column;gap:3px;max-width:70%}
.msg.user .mbody{align-items:flex-end}
.sndr{font-size:10px;color:var(--t4);font-weight:600;letter-spacing:.7px;text-transform:uppercase;padding:0 2px}
.bub{padding:11px 15px;border-radius:12px;font-size:13.5px;line-height:1.65;white-space:pre-wrap;word-break:break-word}
.bub.nx{background:var(--surface);border:1px solid var(--border);border-top-left-radius:3px;color:var(--t2);box-shadow:var(--sh-s)}
.bub.us{background:var(--blue);color:#fff;border-top-right-radius:3px;box-shadow:0 2px 8px rgba(37,99,235,.28)}
.tevt{display:flex;align-items:center;gap:7px;padding:4px 11px;margin-left:42px;border-radius:5px;border:1px solid var(--border);background:var(--panel);font-size:11.5px;color:var(--t3);width:fit-content}
.tic{width:17px;height:17px;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:10px;flex-shrink:0}
.tic.c{background:#fef9c3;color:#854d0e}.tic.d{background:var(--green-l);color:var(--green)}
.tbub{display:flex;align-items:center;gap:4px;padding:11px 15px;background:var(--surface);border:1px solid var(--border);border-radius:12px;border-top-left-radius:3px;box-shadow:var(--sh-s)}
@keyframes td{0%,80%,100%{transform:scale(.55);opacity:.3}40%{transform:scale(1);opacity:1}}
.tbub span{width:6px;height:6px;border-radius:50%;background:var(--t4);display:inline-block;animation:td 1.2s ease infinite}
.tbub span:nth-child(2){animation-delay:.18s}.tbub span:nth-child(3){animation-delay:.36s}
.pid-card{margin:6px 0;padding:14px 18px;background:linear-gradient(135deg,#eff6ff,#dbeafe);border:2px solid var(--blue-m);border-radius:13px;box-shadow:0 3px 12px rgba(37,99,235,.14);max-width:300px}
.pid-lbl{font-size:10px;text-transform:uppercase;letter-spacing:1.2px;color:var(--blue);font-weight:700;margin-bottom:7px}
.pid-val{font-size:24px;font-family:var(--fh);font-weight:800;color:var(--blue);letter-spacing:3px;padding:6px 12px;background:rgba(255,255,255,.75);border-radius:7px;display:inline-block;margin-bottom:7px}
.pid-note{font-size:11.5px;color:var(--t3);line-height:1.45}
.pid-note b{color:var(--orange)}

/* ── DOCTOR CARDS — name only, no meta tags ── */
.doc-cards{display:flex;flex-direction:column;gap:8px;margin:6px 0;max-width:380px}
.doc-card{background:var(--surface);border:1.5px solid var(--border);border-radius:12px;padding:14px 16px;cursor:pointer;transition:all .18s;box-shadow:var(--sh-s);position:relative;overflow:hidden;display:flex;align-items:center;gap:12px;}
.doc-card::before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--blue);border-radius:4px 0 0 4px}
.doc-card:hover{border-color:var(--blue);box-shadow:0 4px 20px rgba(37,99,235,.16);transform:translateY(-2px)}
.doc-av{width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,var(--blue-l),var(--blue-m));display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}
.doc-info{flex:1}
.doc-name{font-weight:700;font-size:14px;color:var(--text);font-family:var(--fh)}
.doc-spec{font-size:11.5px;color:var(--blue);font-weight:600;margin-top:2px}
.select-doc-btn{padding:6px 14px;border-radius:7px;border:none;background:var(--blue);color:#fff;font-size:12px;font-weight:600;cursor:pointer;font-family:var(--font);transition:all .15s;white-space:nowrap;flex-shrink:0}
.select-doc-btn:hover{background:#1d4ed8}

/* ── SLOT PICKER ── */
.slot-section{margin:6px 0;max-width:420px}
.slot-header{font-size:12.5px;font-weight:600;color:var(--t2);margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border)}
.slot-grid{display:flex;flex-wrap:wrap;gap:8px}
.slot-btn{padding:8px 14px;border-radius:8px;border:1.5px solid var(--border);background:var(--surface);color:var(--t2);font-size:13px;font-weight:500;cursor:pointer;transition:all .15s;font-family:var(--font);box-shadow:var(--sh-s)}
.slot-btn:hover{border-color:var(--blue);color:var(--blue);background:var(--blue-d);transform:translateY(-1px)}
.no-slots{font-size:13px;color:var(--t3);padding:12px;background:var(--panel);border-radius:8px;border:1px solid var(--border)}
.inputbar{background:var(--surface);border-top:1px solid var(--border);display:flex;align-items:center;padding:0 18px;gap:10px;box-shadow:0 -2px 10px rgba(0,0,0,.05)}
.iw{flex:1;display:flex;align-items:center;background:var(--panel);border:1.5px solid var(--border);border-radius:10px;padding:0 14px;transition:border-color .2s}
.iw:focus-within{border-color:var(--blue);background:var(--surface)}
.ci{flex:1;background:transparent;border:none;outline:none;color:var(--text);font-family:var(--font);font-size:14px;padding:13px 0}
.ci::placeholder{color:var(--t4)}
.sb{height:40px;padding:0 20px;border-radius:8px;border:none;background:var(--blue);color:#fff;font-size:13px;font-weight:600;cursor:pointer;font-family:var(--font);transition:all .15s;white-space:nowrap;flex-shrink:0;box-shadow:0 2px 8px rgba(37,99,235,.3)}
.sb:hover{background:#1d4ed8;transform:translateY(-1px)}
.sb:disabled{opacity:.5;cursor:not-allowed;transform:none}
@keyframes fu{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
.new{animation:fu .2s ease both}
</style>
</head>
<body>
<div class="app">
<header>
  <div class="logo-mark">N</div>
  <div><div class="logo-text">NEXA</div><div class="logo-sub">Hospital Appointment Assistant</div></div>
  <div class="hright">
    <div class="pill"><div class="dot-live"></div>Online</div>
    <span style="font-size:11.5px;color:var(--t4)" id="sid"></span>
    <button class="nsb" onclick="newSession()">+ New Session</button>
  </div>
</header>
<div class="messages" id="msgs"></div>
<div class="inputbar">
  <div class="iw">
    <input class="ci" id="ci" autofocus autocomplete="off"
      placeholder="Describe your concern or type a doctor's name…"
      onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}"/>
  </div>
  <button class="sb" id="sb" onclick="send()">SEND →</button>
</div>
</div>
<script>
let SID = crypto.randomUUID();
let busy = false;
const msgs = document.getElementById('msgs');
document.getElementById('sid').textContent = 'Session ' + SID.slice(0,8);
let bookCtx = { patientName: null, specialty: null, doctor: null, date: null };

const DOCTORS = {
  "Dr. Kavitha Reddy":  {spec:"Dermatology", icon:"🧴", slots:{Monday:["09:00 AM","10:00 AM","11:00 AM","02:00 PM","03:00 PM","04:00 PM"],Tuesday:["09:00 AM","10:00 AM","11:00 AM","02:00 PM","04:00 PM"],Wednesday:["10:00 AM","11:00 AM","03:00 PM","04:00 PM","05:00 PM"],Thursday:["09:00 AM","10:00 AM","02:00 PM","03:00 PM"],Friday:["09:00 AM","11:00 AM","02:00 PM","04:00 PM"],Saturday:["09:00 AM","10:00 AM","11:00 AM"],Sunday:[]}},
  "Dr. Arjun Sharma":   {spec:"Dermatology", icon:"🩺", slots:{Monday:["10:00 AM","11:00 AM","12:00 PM","03:00 PM","05:00 PM","06:00 PM"],Tuesday:["10:00 AM","12:00 PM","03:00 PM","05:00 PM","06:00 PM"],Wednesday:["11:00 AM","12:00 PM","04:00 PM","05:00 PM","06:00 PM"],Thursday:["10:00 AM","11:00 AM","03:00 PM","05:00 PM","06:00 PM"],Friday:["10:00 AM","12:00 PM","05:00 PM","06:00 PM"],Saturday:["10:00 AM","11:00 AM","12:00 PM","01:00 PM"],Sunday:[]}},
  "Dr. Priya Nair":     {spec:"Cardiology", icon:"❤️", slots:{Monday:["08:00 AM","09:00 AM","10:00 AM","02:00 PM","03:00 PM"],Tuesday:["08:00 AM","09:00 AM","02:00 PM","03:00 PM","04:00 PM"],Wednesday:["08:00 AM","10:00 AM","02:00 PM","04:00 PM"],Thursday:["09:00 AM","10:00 AM","02:00 PM","03:00 PM","04:00 PM"],Friday:["08:00 AM","09:00 AM","02:00 PM"],Saturday:["09:00 AM","10:00 AM"],Sunday:[]}},
  "Dr. Venkat Rao":     {spec:"Orthopedics", icon:"🦴", slots:{Monday:["09:00 AM","10:00 AM","11:00 AM","03:00 PM","04:00 PM","05:00 PM"],Tuesday:["09:00 AM","11:00 AM","03:00 PM","05:00 PM"],Wednesday:["10:00 AM","11:00 AM","12:00 PM","04:00 PM","05:00 PM"],Thursday:["09:00 AM","10:00 AM","03:00 PM","04:00 PM","05:00 PM"],Friday:["09:00 AM","11:00 AM","03:00 PM","05:00 PM"],Saturday:["09:00 AM","10:00 AM","11:00 AM","12:00 PM"],Sunday:[]}},
  "Dr. Meena Krishnan": {spec:"Pediatrics", icon:"👶", slots:{Monday:["09:00 AM","10:00 AM","11:00 AM","12:00 PM","04:00 PM","05:00 PM"],Tuesday:["09:00 AM","10:00 AM","11:00 AM","04:00 PM","05:00 PM"],Wednesday:["09:00 AM","11:00 AM","12:00 PM","04:00 PM","05:00 PM"],Thursday:["09:00 AM","10:00 AM","11:00 AM","04:00 PM","05:00 PM"],Friday:["09:00 AM","10:00 AM","04:00 PM","05:00 PM"],Saturday:["09:00 AM","10:00 AM","11:00 AM","12:00 PM"],Sunday:["10:00 AM","11:00 AM"]}},
  "Dr. Ravi Shankar":   {spec:"General Medicine", icon:"💊", slots:{Monday:["08:00 AM","09:00 AM","10:00 AM","11:00 AM","02:00 PM","03:00 PM","04:00 PM","05:00 PM"],Tuesday:["08:00 AM","09:00 AM","10:00 AM","02:00 PM","03:00 PM","04:00 PM","05:00 PM"],Wednesday:["08:00 AM","09:00 AM","11:00 AM","02:00 PM","04:00 PM","05:00 PM"],Thursday:["08:00 AM","09:00 AM","10:00 AM","02:00 PM","03:00 PM","05:00 PM"],Friday:["08:00 AM","09:00 AM","10:00 AM","02:00 PM","03:00 PM","04:00 PM"],Saturday:["08:00 AM","09:00 AM","10:00 AM","11:00 AM","12:00 PM"],Sunday:["09:00 AM","10:00 AM"]}},
  "Dr. Sunita Patel":   {spec:"Gynecology", icon:"🌸", slots:{Monday:["10:00 AM","11:00 AM","12:00 PM","03:00 PM","04:00 PM","05:00 PM"],Tuesday:["10:00 AM","11:00 AM","03:00 PM","04:00 PM","05:00 PM"],Wednesday:["10:00 AM","12:00 PM","03:00 PM","05:00 PM"],Thursday:["10:00 AM","11:00 AM","12:00 PM","03:00 PM","04:00 PM"],Friday:["10:00 AM","11:00 AM","03:00 PM","04:00 PM"],Saturday:["10:00 AM","11:00 AM","12:00 PM"],Sunday:[]}},
  "Dr. Anil Kumar":     {spec:"Neurology", icon:"🧠", slots:{Monday:["09:00 AM","10:00 AM","02:00 PM","03:00 PM"],Tuesday:["09:00 AM","11:00 AM","02:00 PM","04:00 PM"],Wednesday:["10:00 AM","11:00 AM","03:00 PM","04:00 PM"],Thursday:["09:00 AM","10:00 AM","02:00 PM","03:00 PM"],Friday:["09:00 AM","11:00 AM","02:00 PM"],Saturday:["09:00 AM","10:00 AM"],Sunday:[]}},
};

function getDay(dateStr){
  const days=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
  let d;
  const lo=dateStr.toLowerCase();
  if(lo==='today'||lo==='now') d=new Date();
  else if(lo==='tomorrow'){d=new Date();d.setDate(d.getDate()+1);}
  else{const t=new Date(dateStr);if(!isNaN(t))d=t;}
  return d?days[d.getDay()]:days[new Date().getDay()];
}
function getDateStr(offset=0){
  const d=new Date();d.setDate(d.getDate()+offset);
  return d.toLocaleDateString('en-IN',{day:'numeric',month:'long',year:'numeric'});
}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function sc(){msgs.scrollTop=msgs.scrollHeight}

function appendUser(text){
  const d=document.createElement('div');d.className='msg user new';
  d.innerHTML=`<div class="av us">👤</div><div class="mbody"><span class="sndr">You</span><div class="bub us">${esc(text)}</div></div>`;
  msgs.appendChild(d);sc();
}
function appendTool(tool,type){
  const d=document.createElement('div');d.className='tevt new';
  d.innerHTML=`<div class="tic ${type==='call'?'c':'d'}">${type==='call'?'⚡':'✓'}</div><span>${esc(tool.replace(/_/g,' '))}</span>`;
  msgs.appendChild(d);sc();
}
let typEl=null;
function showTyping(){
  const w=document.createElement('div');w.className='msg new';
  w.innerHTML=`<div class="av nx">NX</div><div class="mbody"><span class="sndr">NEXA</span><div class="tbub"><span></span><span></span><span></span></div></div>`;
  msgs.appendChild(w);sc();typEl=w;
}
function hideTyping(){if(typEl){typEl.remove();typEl=null;}}

let cBub=null,cAgent=null,cWrap=null,cText='';
function ensureBub(agent){
  if(cAgent!==agent){finBub();cAgent=agent;cText='';
    const w=document.createElement('div');w.className='msg new';
    w.innerHTML=`<div class="av nx">NX</div><div class="mbody"><span class="sndr">NEXA</span><div class="bub nx"></div></div>`;
    msgs.appendChild(w);cBub=w.querySelector('.bub.nx');cWrap=w.querySelector('.mbody');
  }
}
function appendToken(text,agent){
  hideTyping();ensureBub(agent||'productivity_root');
  cText+=text;cBub.textContent=cText;sc();
}
function finBub(){
  if(cText&&cWrap){
    // inject PAT-XXXX cards only
    const pids=[...new Set((cText.match(/PAT-\d{4}/g)||[]))];
    pids.forEach(pid=>{
      const c=document.createElement('div');c.className='pid-card new';
      c.innerHTML=`<div class="pid-lbl">🪪 Patient ID</div><div class="pid-val">${esc(pid)}</div><div class="pid-note"><b>⚠️ Save this.</b> You'll need it to reschedule or cancel.</div>`;
      cWrap.appendChild(c);
    });
    sc();
  }
  cBub=null;cAgent=null;cWrap=null;cText='';
}

// ── Doctor Cards (name + specialty only) ─────────────────
function showDoctorCards(spec, date){
  const targetDate=date||bookCtx.date||getDateStr(0);
  const day=getDay(targetDate);
  const filtered=Object.entries(DOCTORS).filter(([n,d])=>d.spec.toLowerCase()===spec.toLowerCase());
  if(!filtered.length){appendNexa(`No doctors found for ${spec}.`);return;}
  const w=document.createElement('div');w.className='msg new';
  const cards=document.createElement('div');cards.className='doc-cards';
  filtered.forEach(([name,info])=>{
    const card=document.createElement('div');card.className='doc-card';
    card.innerHTML=`
      <div class="doc-av">${info.icon}</div>
      <div class="doc-info">
        <div class="doc-name">${esc(name)}</div>
        <div class="doc-spec">${esc(info.spec)}</div>
      </div>
      <button class="select-doc-btn">Select →</button>`;
    card.querySelector('.select-doc-btn').onclick=()=>{selectDoctor(name,targetDate);w.remove();};
    cards.appendChild(card);
  });
  const wrap=document.createElement('div');wrap.className='mbody';
  const lbl=document.createElement('span');lbl.className='sndr';lbl.textContent='NEXA';
  const hdr=document.createElement('div');hdr.style.cssText='font-size:13px;color:var(--t3);margin-bottom:8px;font-weight:500';
  hdr.textContent=`Available ${spec} doctors:`;
  wrap.appendChild(lbl);wrap.appendChild(hdr);wrap.appendChild(cards);
  w.innerHTML='<div class="av nx">NX</div>';w.appendChild(wrap);
  msgs.appendChild(w);sc();
}

function selectDoctor(name,date){
  bookCtx.doctor=name;bookCtx.date=date;
  appendUser(`Select ${name}`);
  showSlotPicker(name,date);
  sendToAgent(`I want to book with ${name} on ${date}`);
}

function showSlotPicker(docName,dateStr){
  const day=getDay(dateStr);
  const info=DOCTORS[docName];
  if(!info){appendNexa('Doctor not found.');return;}
  const slots=info.slots[day]||[];
  const w=document.createElement('div');w.className='msg new';
  const wrap=document.createElement('div');wrap.className='mbody';
  const lbl=document.createElement('span');lbl.className='sndr';lbl.textContent='NEXA';
  wrap.appendChild(lbl);
  const sec=document.createElement('div');sec.className='slot-section';
  sec.innerHTML=`<div class="slot-header">⏰ Available slots — <strong>${esc(docName)}</strong> on <strong>${day}, ${esc(dateStr)}</strong></div>`;
  if(!slots.length){
    sec.innerHTML+=`<div class="no-slots">😔 No slots on ${day}. Try another date.</div>`;
    const nav=document.createElement('div');nav.style.cssText='display:flex;gap:8px;margin-top:10px;flex-wrap:wrap';
    [1,2,3,4,5].forEach(offset=>{
      const nd=new Date();nd.setDate(nd.getDate()+offset);
      const nds=nd.toLocaleDateString('en-IN',{day:'numeric',month:'long',year:'numeric'});
      const nday=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"][nd.getDay()];
      const ns=DOCTORS[docName]?.slots[nday]||[];
      if(ns.length){const b=document.createElement('button');b.className='slot-btn';b.textContent=`${nday} (${ns.length})`;b.onclick=()=>{w.remove();showSlotPicker(docName,nds);};nav.appendChild(b);}
    });
    sec.appendChild(nav);
  } else {
    const grid=document.createElement('div');grid.className='slot-grid';
    slots.forEach(s=>{const b=document.createElement('button');b.className='slot-btn';b.textContent=s;b.onclick=()=>{selectSlot(s);w.remove();};grid.appendChild(b);});
    sec.appendChild(grid);
  }
  wrap.appendChild(sec);
  w.innerHTML='<div class="av nx">NX</div>';w.appendChild(wrap);
  msgs.appendChild(w);sc();
}

function selectSlot(slot){
  bookCtx.slot=slot;
  appendUser(`Select slot ${slot}`);
  sendToAgent(`Book appointment for ${bookCtx.patientName||'the patient'} with ${bookCtx.doctor} on ${bookCtx.date} at ${slot}`);
}

function appendNexa(text){
  const w=document.createElement('div');w.className='msg new';
  w.innerHTML=`<div class="av nx">NX</div><div class="mbody"><span class="sndr">NEXA</span><div class="bub nx">${esc(text)}</div></div>`;
  msgs.appendChild(w);sc();
}
function appendErr(text){
  const w=document.createElement('div');w.className='msg new';
  w.innerHTML=`<div class="av nx">NX</div><div class="mbody"><span class="sndr">NEXA</span><div class="bub nx" style="color:var(--red);border-color:#fecaca">⚠️ ${esc(text)}</div></div>`;
  msgs.appendChild(w);sc();
}

async function streamMsg(message){
  const res=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:SID,message})});
  if(!res.ok) throw new Error(`HTTP ${res.status}`);
  const reader=res.body.getReader(),dec=new TextDecoder();
  let buf='';
  while(true){
    const{done,value}=await reader.read();if(done)break;
    buf+=dec.decode(value,{stream:true});
    const lines=buf.split('\n');buf=lines.pop();
    for(const line of lines){
      if(!line.startsWith('data:'))continue;
      const raw=line.slice(5).trim();if(!raw)continue;
      try{
        const e=JSON.parse(raw);
        if(e.type==='token') appendToken(e.text,e.agent);
        else if(e.type==='tool_call') appendTool(e.tool,'call');
        else if(e.type==='tool_result') appendTool(e.tool,'done');
        else if(e.type==='error'){hideTyping();finBub();appendErr(e.text);}
        else if(e.type==='done'){hideTyping();finBub();}
        // show doctor cards when agent lists doctors
        if(e.type==='tool_result'&&e.tool==='get_doctors_by_specialty'&&bookCtx.specialty){
          setTimeout(()=>showDoctorCards(bookCtx.specialty),100);
        }
      }catch(_){}
    }
  }
}

async function sendToAgent(msg){
  busy=true;document.getElementById('sb').disabled=true;
  showTyping();
  try{await streamMsg(msg);}
  catch(e){hideTyping();finBub();appendErr(e.message);}
  busy=false;document.getElementById('sb').disabled=false;
  document.getElementById('ci').focus();
}

async function send(){
  if(busy)return;
  const inp=document.getElementById('ci');
  const text=inp.value.trim();if(!text)return;
  inp.value='';
  const lo=text.toLowerCase();
  if(bookCtx.specialty&&!bookCtx.patientName&&/my name is|i am|name:/i.test(lo)){
    const m=text.match(/(?:my name is|i am|name:)\s*([a-zA-Z\s]+)/i);
    if(m)bookCtx.patientName=m[1].trim();
  }
  // detect specialty from user message
  const specMap={'dermatology':'Dermatology','cardiology':'Cardiology','orthopedics':'Orthopedics','pediatrics':'Pediatrics','general medicine':'General Medicine','gynecology':'Gynecology','neurology':'Neurology'};
  for(const[k,v] of Object.entries(specMap)){
    if(lo.includes(k)){bookCtx.specialty=v;break;}
  }
  appendUser(text);
  await sendToAgent(text);
}

function newSession(){
  SID=crypto.randomUUID();
  document.getElementById('sid').textContent='Session '+SID.slice(0,8);
  msgs.innerHTML='';cBub=null;cAgent=null;cWrap=null;cText='';
  bookCtx={patientName:null,specialty:null,doctor:null,date:null};
  busy=false;document.getElementById('sb').disabled=false;
  document.getElementById('ci').focus();
  setTimeout(()=>sendToAgent('hi'),300);
}

window.addEventListener('DOMContentLoaded',()=>{
  setTimeout(()=>{
    busy=true;showTyping();
    streamMsg('hi').then(()=>{busy=false;document.getElementById('sb').disabled=false;})
    .catch(e=>{hideTyping();finBub();appendErr(e.message);busy=false;document.getElementById('sb').disabled=false;});
  },400);
});
</script>
</body>
</html>"""

app = FastAPI(title="NEXA Hospital")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
async def root(): return HTML

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    sid  = body.get("session_id", str(uuid.uuid4()))
    msg  = body.get("message","").strip()
    if not msg: return JSONResponse({"error":"empty"}, status_code=400)
    return StreamingResponse(call_agent(sid, msg), media_type="text/event-stream",
                             headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.get("/health")
async def health():
    return {"status":"ok","adk":ADK_AVAILABLE}

if __name__=="__main__":
    print("\n"+"─"*28)
    print("  NEXA — Hospital Appointment Assistant")
    print(f"  ADK: {ADK_AVAILABLE}  |  http://0.0.0.0:8080")
    print("─"*28+"\n")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")