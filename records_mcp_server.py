import asyncio, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from database import init_db, db_save_note, db_get_notes

init_db()
server = Server("patient-records")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name="save_patient_note",
            description="Save a patient note or medical record",
            inputSchema={"type":"object","properties":{
                "note":{"type":"string"},
                "title":{"type":"string"}
            },"required":["note"]}),
        types.Tool(name="get_patient_notes",
            description="Get all patient notes and medical records",
            inputSchema={"type":"object","properties":{}})
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "save_patient_note":
        result = db_save_note(arguments["note"], arguments.get("title"))
        return [types.TextContent(type="text", text=f"✅ Patient note saved (ID:{result['id']})")]
    elif name == "get_patient_notes":
        notes = db_get_notes()
        if not notes:
            return [types.TextContent(type="text", text="No patient notes found.")]
        lines = [f"[{n['id']}] {n['title'] or 'Untitled'}: {n['content'][:80]}" for n in notes]
        return [types.TextContent(type="text", text="\n".join(lines))]

async def main():
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
