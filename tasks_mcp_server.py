import asyncio, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from database import init_db, db_add_task, db_get_tasks, db_complete_task

init_db()
server = Server("task-manager")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name="add_task", description="Add a task with priority",
            inputSchema={"type":"object","properties":{"task":{"type":"string"},"priority":{"type":"string","enum":["low","normal","high"]}},"required":["task"]}),
        types.Tool(name="get_tasks", description="Get all pending tasks",
            inputSchema={"type":"object","properties":{}}),
        types.Tool(name="complete_task", description="Complete a task by ID",
            inputSchema={"type":"object","properties":{"task_id":{"type":"integer"}},"required":["task_id"]})
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "add_task":
        result = db_add_task(arguments["task"], arguments.get("priority","normal"))
        return [types.TextContent(type="text", text=f"✅ Task added (ID:{result['id']}): {arguments['task']}")]
    elif name == "get_tasks":
        tasks = db_get_tasks("pending")
        if not tasks: return [types.TextContent(type="text", text="No pending tasks!")]
        lines = [f"[{t['id']}] [{t['priority'].upper()}] {t['task']}" for t in tasks]
        return [types.TextContent(type="text", text="\n".join(lines))]
    elif name == "complete_task":
        result = db_complete_task(arguments["task_id"])
        return [types.TextContent(type="text", text=str(result))]

async def main():
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
