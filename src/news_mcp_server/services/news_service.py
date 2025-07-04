from typing import Optional, List
from ..clients.elastic_client import AsyncElasticClient
from ..schemas.news import NewsBaseItem, NewsDetailItem
from ..config.settings import es_settings

class NewsService:
    def __init__(self, client: AsyncElasticClient):
        self.client = client

    async def search_news(
        self,
        query: str,
        max_results: int = 10,
        source: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[NewsBaseItem]:
        """按关键词、来源、时间范围搜索新闻，并返回 NewsItem 列表"""
        limit = min(max_results, es_settings.MAX_RESULTS_LIMIT)

        items = await self.client.search_news(
            query=query,
            source=source,
            date_from=date_from,
            date_to=date_to,
            max_results=limit
        )
        return [NewsBaseItem(**item) for item in items]

    async def read_news(self, news_id: str) -> NewsDetailItem:
        """按 news_id 获取单条新闻，并返回 NewsDetailItem"""
        data = await self.client.get_by_id(news_id)
        return NewsDetailItem(**data)

    async def search_news_with_secondary_filter(self,
                                              primary_query: str,
                                              secondary_query: str,
                                              max_results: int = 10,
                                              source: Optional[str] = None,
                                              date_from: Optional[str] = None,
                                              date_to: Optional[str] = None) -> List[NewsBaseItem]:
        """
        按主、次查询词联合搜索新闻，并包装为 NewsBaseItem 列表
        """
        items = await self.client.search_news_with_secondary_filter(
            primary_query=primary_query,
            secondary_query=secondary_query,
            max_results=max_results,
            source=source,
            date_from=date_from,
            date_to=date_to,
        )
        return [NewsBaseItem(**item) for item in items]

    async def search_topic_news(
            self,
            primary_queries: List[str],
            secondary_query: List[str],
            max_results: int = 10,
            sources: Optional[str] = None,
            search_word=None,
            date_from: Optional[str] = None,
            date_to: Optional[str] = None
    ) -> dict:
        """
        新功能：按多个主关键词(组)与次关键词组合(A&D|B&D|...)搜索新闻，并返回 NewsBaseItem 列表
        """
        items = await self.client.search_topic_news(
            primary_queries=primary_queries,
            secondary_query=secondary_query,
            sources=sources,
            max_results=max_results,
            search_word=search_word,
            date_from=date_from,
            date_to=date_to
        )
        return {
            "total": items.total,
            "data": [NewsBaseItem(**item) for item in items.data]
        }
