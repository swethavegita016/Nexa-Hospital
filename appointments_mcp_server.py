import asyncio, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from database import init_db, db_save_meeting, db_get_meetings

init_db()
server = Server("appointments-manager")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name="book_appointment",
            description="Book a hospital appointment",
            inputSchema={"type":"object","properties":{
                "patient_name":{"type":"string"},
                "doctor":{"type":"string"},
                "department":{"type":"string"},
                "appointment_time":{"type":"string"},
                "reason":{"type":"string"}
            },"required":["patient_name","doctor","department","appointment_time"]}),
        types.Tool(name="get_appointments",
            description="Get all scheduled appointments",
            inputSchema={"type":"object","properties":{}})
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "book_appointment":
        result = db_save_meeting(
            title=f"{arguments['patient_name']} → Dr. {arguments['doctor']} ({arguments['department']})",
            purpose=arguments.get("reason", "General Consultation"),
            meeting_time=arguments["appointment_time"]
        )
        return [types.TextContent(type="text", text=f"✅ Appointment booked (ID:{result['id']}) for {arguments['patient_name']} with Dr. {arguments['doctor']} at {arguments['appointment_time']}")]
    elif name == "get_appointments":
        meetings = db_get_meetings()
        if not meetings:
            return [types.TextContent(type="text", text="No appointments scheduled.")]
        lines = [f"[{m['id']}] {m['title']} | {m['meeting_time']} | {m.get('purpose','N/A')}" for m in meetings]
        return [types.TextContent(type="text", text="\n".join(lines))]

async def main():
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
