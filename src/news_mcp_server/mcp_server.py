from typing import List
from fastmcp import FastMCP, Context
from fastmcp.server.http import Middleware
from pydantic import Field
import contextlib
from .services.news_service import NewsService
from .clients.elastic_client import AsyncElasticClient
from .middlewares.audit import AuditMiddleware
from .utils.logger import logger
logger.info("News MCP module")


class NewsMCP(FastMCP):
    """FastMCP server with authentication middleware."""
    pass

def create_http_app(mcp):
    middlewares = [
        Middleware(AuditMiddleware)
    ]
    mcp_app = mcp.http_app("/es-news-mcp", middleware=middlewares)
    return mcp_app
app_services = {}


@contextlib.asynccontextmanager
async def lifespan(app: FastMCP):
    """Lifespan context manager for FastMCP server."""
    logger.info("Server started")
    es_client = AsyncElasticClient()
    try:
        app_services["news_service"] = NewsService(es_client)
        logger.info("Server started")
        yield
    except Exception as e:
        logger.error("Server error", error=str(e))
        raise e
    finally:
        await es_client.close()
        logger.info("Server closed")


mcp = NewsMCP(
    name="NewsSearchServer",
    instructions="""
        This server provides news search_news tools.
        Call search_news() to get news for marketing research.
        Call read_single_news() to get detailed content of a single news.
    """,
    lifespan=lifespan
)


@mcp.prompt()
async def search_news_prompt():
    return "This is a prompt for search_news"


@mcp.tool(
    name="search_news",
    description="根据关键词搜索新闻。可选参数支持按发布时间范围筛选结果。适用于需要多条件复合筛选新闻的场景。",
    tags={"news search_news engine"}
)
async def search_news(
        query: str = Field(description="请输入用于检索新闻的关键词或短语。例如：'人工智能'、'华为 5G'、'经济形势'。支持单个词、多个词或短语，系统将返回与关键词相关的新闻。"),
        max_results: int  = Field(default=20, description="请输入希望返回的新闻条数（1-100）。默认值为20，最大不超过100。建议根据实际需求设置，避免一次性获取过多数据。"),
        date_from: str = Field(default="", description="请输入起始日期，格式为 YYYY-MM-DD。例如：'2024-06-01'。系统将只返回该日期及之后发布的新闻。可选参数，不填则不限制起始时间。"),
        date_to: str = Field(default="", description="请输入结束日期，格式为 YYYY-MM-DD。例如：'2024-06-12'。系统将只返回该日期及之前发布的新闻。可选参数，不填则不限制结束时间。")
) -> List[dict]:
    """MCP 工具：按关键词、来源、时间范围搜索新闻"""
    logger.info(f"Call Tool search_news {query}")
    news_items = await app_services["news_service"].search_news(
        query=query,
        max_results=max_results,
        source=None,
        date_from=date_from,
        date_to=date_to
    )
    return [item.model_dump() for item in news_items]


@mcp.tool(
    name="search_news_with_secondary_filter",
    description="根据主关键词和次关键词联合检索新闻。该工具会先用主关键词在新闻库中查找相关内容，再用次关键词对结果进行进一步过滤，最终返回同时包含主关键词和次关键词的新闻列表。可选参数还支持按发布时间范围筛选结果。适用于需要多条件复合筛选新闻的场景。"
)
async def search_news_with_secondary_filter(primary_query: str = Field(description="请输入用于检索新闻的关键词或短语。例如：'人工智能'、'华为 5G'、'经济形势'。支持单个词、多个词或短语，系统将返回与关键词相关的新闻。"),
                      secondary_query: str=Field(description="请输入用于过滤新闻的次要关键词或短语。例如：'人工智能'、'华为 5G'、'经济形势'。支持单个词、多个词或短语，系统将返回与次要关键词相关的新闻。"),
                      max_results: int = Field(default=20, description="请输入希望返回的新闻条数（1-100）。默认值为20，最大不超过100。建议根据实际需求设置，避免一次性获取过多数据。"),
                      date_from: str = Field(default="", description="起始日期，格式为 YYYY-MM-DD。系统将只返回该日期及之后发布的新闻"),
                      date_to: str = Field(default="", description="结束日期，格式为 YYYY-MM-DD。系统将只返回该日期及之前发布的新闻")) -> list:
    logger.info(f"Call Tool search_news_with_secondary_filter {primary_query}, {secondary_query}")
    news_items = await app_services["news_service"].search_news_with_secondary_filter(
        primary_query=primary_query,
        secondary_query=secondary_query,
        max_results=max_results,
        source=None,
        date_from=date_from,
        date_to=date_to
    )
    return [item.model_dump() for item in news_items]

@mcp.tool(
    name="read_single_news",
    description="获取新闻详情。该工具会根据给定的新闻ID（news_id），从新闻库中获取完整的新闻内容。通常，news_id 是从 search_news 或 search_news_with_secondary_filter 工具返回结果中的 id 字段获取的。",
)
async def read_single_news( ctx: Context,
                            news_id: str = Field(description="请输入要获取的新闻ID（news_id），通常来源于 search_news/search_news_with_secondary_filter 返回结果中的 id 字段。例如：'600001_1'。")) -> dict:
    """MCP 工具：按 ID 获取单条新闻内容"""
    logger.info(f"Call Tool read_single_news {news_id}\n{ctx.session}")
    news_item = await app_services["news_service"].read_news(news_id)
    return news_item.model_dump()


@mcp.tool(
    name="search_topic_news",
    description="根据多个主关键词列表、筛选词列表(组)、数据源列表以 OR 关系批量查询新闻，支持时间范围筛选. "
                "基本查询逻辑：<label1>&<filtered_words>|<label2>&<filtered_words>|<source1>&<filtered_words>|...|"
                "允许在基本查询逻辑之上再搜索"
)
async def search_topic_news(
    ctx: Context,
    primary_queries: List[str]= Field(
        description="【必填】根据多个主关键词列表，系统返回包含主关键词与次关键词组合，所有组合的结果以OR关系连接的新闻"
    ),
    secondary_querys: List[str] = Field(default_factory=list,
        description="筛选词，将与每个主关键词进行 AND 运算"

    ),
    sources: List[str] = Field(default_factory=list,
        description="数据源列表，将与每个主关键词进行 AND 运算"
    ),
    search_word: str = Field(default="", description="搜索词"),
    max_results: int = Field(
        default=15,
        description="【可选】希望返回的新闻数量，取值1-100，默认10"
    ),
    date_from: str = Field(
        default="",
        description="【可选】起始发布日期，格式 YYYY-MM-DD"
    ),
    date_to: str = Field(
        default="",
        description="【可选】结束发布日期，格式 YYYY-MM-DD"
    )
) -> List[dict]:
    """MCP 工具：按多个主关键词与次关键词组合(A&D|B&D|...)批量搜索新闻"""
    logger.info(f"Call search_topic_news", primary_queries=primary_queries,secondary_query=secondary_querys, ctx=ctx.request_context.request['state'])
    if isinstance(primary_queries, str) and len(primary_queries.strip())>0:
        primary_queries = [primary_queries]
    if len(primary_queries) == 0:
        return []
    if isinstance(secondary_querys, str) and len(secondary_querys.strip())>0:
        secondary_querys = [secondary_querys]
    if isinstance(sources, str) and len(sources.strip())>0:
        sources = [sources]
    news_items = await app_services["news_service"].search_topic_news(
        primary_queries=primary_queries,
        secondary_query=secondary_querys,
        max_results=max_results,
        sources=sources,
        search_word=search_word,
        date_from=date_from,
        date_to=date_to
    )
    logger.info(f"Call search_topic_news", total=news_items.get("total"), primary_queries_count=len(primary_queries),secondary_query_count=len(secondary_querys), ctx=ctx.request_context.request['state'])
    return [item.model_dump() for item in news_items.get("data")]


mcp_app = create_http_app(mcp)
