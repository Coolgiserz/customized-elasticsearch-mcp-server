import asyncio
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from elastic_transport import TransportError
from typing import List
from elasticsearch import AsyncElasticsearch
from ..config.settings import es_settings
from ..exceptions import ToolException
from ..utils.logger import logger


OUTPUT_SOURCE_FIELDS = ['news_id', 'title', 'source', 'url', 'release_time']


class AsyncElasticClient:
    @dataclass
    class SearchResponse:
        data: List[dict]
        total: int = 0

    def __init__(self):
        # 初始化异步 ElasticSearch 客户端
        self._client = AsyncElasticsearch(es_settings.URL,
                                          api_key=es_settings.api_key, verify_certs=False)
        self.index = es_settings.ES_INDEX

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=(
                retry_if_exception_type(TransportError) |
                retry_if_exception_type(asyncio.TimeoutError)
        ),
    )
    async def search_news(self, query: str, source: str = None, date_from: str = None, date_to: str = None, max_results: int = 10) -> list:
        """
        ElasticSearch 异步搜索新闻
        """
        must_clauses = []
        if query:
            must_clauses.append({'multi_match': {'query': query,
                                                 'fields': ['title', 'content']}})
        if source:
            must_clauses.append({'term': {'source.keyword': source}})
        if date_from or date_to:
            range_filter = {}
            if date_from:
                range_filter['gte'] = date_from
            if date_to:
                range_filter['lte'] = date_to
            must_clauses.append({'range': {'release_time': range_filter}})

        if must_clauses:
            body = {'query': {'bool': {'must': must_clauses}}}
        else:
            body = {'query': {'match_all': {}}}

        response = await self._client.search(index=self.index,
                                             body=body,
                                             size=max_results,
                                             source_includes=OUTPUT_SOURCE_FIELDS)
        hits = response.get('hits', {}).get('hits', [])
        return [hit.get('_source', {}) for hit in hits]

    async def search_news_with_secondary_filter(
        self,
        primary_query: str,
        secondary_query: str,
        max_results: int = 10,
        source: str = None,
        date_from: str = None,
        date_to: str = None
    ) -> list:
        """
        异步联合搜索：按主查询词和次查询词搜索新闻，支持来源和时间范围过滤
        """
        logger.info(f"search_news_with_secondary_filter: {primary_query}, {secondary_query}")
        # 限制最大返回结果数
        limit = min(max_results, es_settings.MAX_RESULTS_LIMIT)
        # 构建 bool must 子句
        must_clauses = []
        if primary_query:
            must_clauses.append({'multi_match': {'query': primary_query, 'fields': ['title', 'content']}})
        if secondary_query:
            must_clauses.append({'multi_match': {'query': secondary_query, 'fields': ['title', 'content']}})
        if source:
            must_clauses.append({'term': {'source.keyword': source}})
        if date_from or date_to:
            range_filter = {}
            if date_from:
                range_filter['gte'] = date_from
            if date_to:
                range_filter['lte'] = date_to
            must_clauses.append({'range': {'release_time': range_filter}})

        # 构建查询主体
        if must_clauses:
            body = {'query': {'bool': {'must': must_clauses}}}
        else:
            body = {'query': {'match_all': {}}}

        # 执行搜索
        response = await self._client.search(
            index=self.index,
            body=body,
            size=limit,
            source_includes=OUTPUT_SOURCE_FIELDS
        )
        hits = response.get('hits', {}).get('hits', [])
        return [hit.get('_source', {}) for hit in hits]

    async def get_by_id(self, news_id: str) -> dict:
        """
        ElasticSearch 异步按 ID 查询单条新闻
        """
        try:
            body = {
                "query": {
                    "match": {
                        "news_id": news_id
                    }
                }
            }
            response = await self._client.search(index=self.index,
                                                 body=body,
                                                 source_includes=OUTPUT_SOURCE_FIELDS,
                                                 size=1)
            hits = response.get('hits', {}).get('hits', [])
            return hits[0].get('_source', {}) if hits else {}
        except Exception:
            raise ToolException(f'Tool call exception with news_id {news_id}')

    def _append_common_filters(self, must: list, search_word: str, date_from: str, date_to: str):
        """提炼公共过滤器: 添加 search_word 和时间范围到 must 列表"""
        if search_word:
            must.append({
                'multi_match': {
                    'query': search_word,
                    'fields': ['title^5', 'content'],
                    'operator': 'and'
                }
            })
        if date_from or date_to:
            range_filter = {}
            if date_from:
                range_filter['gte'] = date_from
            if date_to:
                range_filter['lte'] = date_to
            must.append({'range': {'release_time': range_filter}})

    def _add_clauses(self, should_clauses: list, base_filters: list, secondary_queries: list[str], search_word: str, date_from: str, date_to: str):
        """根据 base_filters 和 secondary_queries 构建子句并添加到 should_clauses"""
        if secondary_queries:
            for sec in secondary_queries:
                must = base_filters + [{'match_phrase': {'title': sec}}]
                self._append_common_filters(must, search_word, date_from, date_to)
                should_clauses.append({'bool': {'must': must}})
        else:
            must = base_filters.copy()
            self._append_common_filters(must, search_word, date_from, date_to)
            should_clauses.append({'bool': {'must': must}})

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=(
            retry_if_exception_type(TransportError) |
            retry_if_exception_type(asyncio.TimeoutError)
        ),
    )
    async def search_topic_news(
            self,
            primary_queries: List[str],
            secondary_query: List[str]=None,
            max_results: int = 10,
            sources: List[str] = None,
            search_word=None,
            date_from: str = None,
            date_to: str = None
    ) -> SearchResponse:
        """
        "根据多个标签列表、筛选词列表(组)、数据源列表以 OR 关系批量查询新闻，支持时间范围筛选. "
        "基本查询逻辑：<label1>&<filtered_words>|<label2>&<filtered_words>|<source1>&<filtered_words>|...|"
        "允许在基本查询逻辑之上再搜索"
        """
        limit = min(max_results, es_settings.MAX_RESULTS_LIMIT)
        secondary_queries = secondary_query or []
        should_clauses = []
        for primary in primary_queries or []:
            self._add_clauses(should_clauses, [{'match_phrase': {'title': primary}}], secondary_queries, search_word, date_from, date_to)
        for source in sources or []:
            self._add_clauses(should_clauses, [{'term': {'source.keyword': source}}], secondary_queries, search_word, date_from, date_to)
        body = {'query': {'bool': {'should': should_clauses}}}
        # 按发布日期降序排序
        body['sort'] = [{'release_time': {'order': 'desc'}}]

        response = await self._client.search(
            index=self.index,
            body=body,
            size=limit,
            source_includes=OUTPUT_SOURCE_FIELDS
        )
        raw_hits = response.get('hits', {})
        hits = raw_hits.get('hits', [])
        total = raw_hits.get("total", {}).get("value", 0)
        return self.SearchResponse(data=[hit.get('_source', {}) for hit in hits], total=total)


    async def close(self):
        await self._client.close()