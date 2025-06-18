import pytest
from fastmcp import Client
from src.news_mcp_server.mcp_server import mcp


@pytest.mark.asyncio
async def test_mcp_client():
    async with Client(mcp) as client:
        # use the client
        tools = await client.list_tools()
        print(f"Available tools: {tools}")
        assert len(tools) > 0, "No tools found"
        result = await client.call_tool("search_news", {"query": "实验"})
        print(f"Result: {result}")