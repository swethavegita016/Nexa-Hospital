import asyncio, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from database import init_db, db_add_task, db_get_tasks

init_db()
server = Server("urgent-cases")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name="flag_urgent",
            description="Flag a patient case as urgent or emergency",
            inputSchema={"type":"object","properties":{
                "patient_name":{"type":"string"},
                "symptoms":{"type":"string"}
            },"required":["patient_name","symptoms"]}),
        types.Tool(name="get_urgent_cases",
            description="Get all active urgent cases",
            inputSchema={"type":"object","properties":{}})
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "flag_urgent":
        result = db_add_task(
            task=f"🚨 URGENT: {arguments['patient_name']} — {arguments['symptoms']}",
            priority="high"
        )
        return [types.TextContent(type="text", text=f"🚨 Case flagged as URGENT (ID:{result['id']}). Staff alerted for {arguments['patient_name']}.")]
    elif name == "get_urgent_cases":
        tasks = db_get_tasks("pending")
        urgent = [t for t in tasks if t["priority"] == "high"]
        if not urgent:
            return [types.TextContent(type="text", text="No urgent cases at this time.")]
        lines = [f"[{t['id']}] {t['task']}" for t in urgent]
        return [types.TextContent(type="text", text="\n".join(lines))]

async def main():
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
