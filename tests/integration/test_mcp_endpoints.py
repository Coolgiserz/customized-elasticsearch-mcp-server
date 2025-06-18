import pytest
from fastmcp import Client
from src.news_mcp_server.mcp_server import mcp
import os, time, asyncio

@pytest.mark.asyncio
async def test_mcp_client():
    async with Client(mcp) as client:
        # use the client
        tools = await client.list_tools()
        print(f"Available tools: {tools}")
        assert len(tools) > 0, "No tools found"
        result = await client.call_tool("search_news", {"query": "实验"})
        print(f"Result: {result}")


@pytest.mark.asyncio
@pytest.mark.parametrize("concurrency", [10, 50, 100, 500, 1000, 5000])
async def test_mcp_concurrency(concurrency):
    """
    On my Macbook Pro M2 Pro, the result is as follows:
    PASSED                   [ 16%]并发: 10, 成功: 10, 失败: 0, 平均耗时: 0.207s, P95: 0.234s
    PASSED                   [ 33%]并发: 50, 成功: 50, 失败: 0, 平均耗时: 0.404s, P95: 0.461s
    PASSED                  [ 50%]并发: 100, 成功: 100, 失败: 0, 平均耗时: 0.899s, P95: 1.148s
    PASSED                  [ 66%]并发: 500, 成功: 500, 失败: 0, 平均耗时: 7.679s, P95: 11.930s
    PASSED                 [ 83%]并发: 1000, 成功: 1000, 失败: 0, 平均耗时: 21.783s, P95: 36.699s
    """
    url = os.getenv("MCP_URL", "http://127.0.0.1:28000/mcp-server/es-news-mcp")
    async with Client(url) as client:
        # 并发任务函数
        async def worker(idx):
            start = time.perf_counter()
            try:
                await client.call_tool("search_news", {"query": "测试"})
                status = "ok"
            except Exception as e:
                status = "error"
            latency = time.perf_counter() - start
            return status, latency

        # 三阶段：灌入期、稳态期、退载期
        # 简化版：一次性发起 concurrency 个请求
        tasks = [asyncio.create_task(worker(i)) for i in range(concurrency)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计
        ok = sum(1 for r in results if isinstance(r, tuple) and r[0]=="ok")
        err = sum(1 for r in results if r[0]=="error" or isinstance(r, Exception))
        latencies = [r[1] for r in results if isinstance(r, tuple)]
        avg_latency = sum(latencies) / len(latencies)
        p95 = sorted(latencies)[int(len(latencies)*0.95)]

        print(f"并发: {concurrency}, 成功: {ok}, 失败: {err}, 平均耗时: {avg_latency:.3f}s, P95: {p95:.3f}s")
        assert err == 0, f"有 {err} 请求失败"