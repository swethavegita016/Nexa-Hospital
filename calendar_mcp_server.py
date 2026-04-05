import asyncio
import json
from datetime import datetime, timedelta
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

SCOPES = ['https://www.googleapis.com/auth/calendar']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

server = Server("google-calendar")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="create_calendar_event",
            description="Create a Google Calendar event",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Event title"},
                    "start_time": {"type": "string", "description": "Start time e.g. '2025-04-10 10:00'"},
                    "end_time": {"type": "string", "description": "End time e.g. '2025-04-10 11:00'"},
                    "description": {"type": "string", "description": "Event description"}
                },
                "required": ["title", "start_time"]
            }
        ),
        types.Tool(
            name="list_calendar_events",
            description="List upcoming Google Calendar events",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Max events to return", "default": 10}
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    service = get_calendar_service()
    
    if name == "create_calendar_event":
        title = arguments["title"]
        start_str = arguments["start_time"]
        end_str = arguments.get("end_time", "")
        description = arguments.get("description", "")
        
        # Parse start time
        try:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        except:
            start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
        
        # Default end = 1 hour after start
        if end_str:
            try:
                end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
            except:
                end_dt = start_dt + timedelta(hours=1)
        else:
            end_dt = start_dt + timedelta(hours=1)
        
        event = {
            'summary': title,
            'description': description,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
        }
        result = service.events().insert(calendarId='primary', body=event).execute()
        return [types.TextContent(type="text", text=f"✅ Event created: {result.get('htmlLink')}")]
    
    elif name == "list_calendar_events":
        max_results = arguments.get("max_results", 10)
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        if not events:
            return [types.TextContent(type="text", text="No upcoming events found.")]
        lines = []
        for e in events:
            start = e['start'].get('dateTime', e['start'].get('date'))
            lines.append(f"• {e['summary']} — {start}")
        return [types.TextContent(type="text", text="\n".join(lines))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
