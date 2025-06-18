from elasticsearch import AsyncElasticsearch
from ..config.settings import es_settings
from ..exceptions import ToolException
from ..utils.logger import logger


OUTPUT_SOURCE_FIELDS = ['news_id', 'title', 'source', 'url', 'release_time']


class AsyncElasticClient:
    def __init__(self):
        # 初始化异步 ElasticSearch 客户端
        self._client = AsyncElasticsearch(es_settings.URL,
                                          api_key=es_settings.api_key, verify_certs=False)
        self.index = es_settings.ES_INDEX

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

    async def close(self):
        await self._client.close()