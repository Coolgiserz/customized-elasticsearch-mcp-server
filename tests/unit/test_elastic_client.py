import pytest
from src.news_mcp_server.clients.elastic_client import AsyncElasticClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_search_success():
    client = AsyncElasticClient()
    fake_hits = [{'_source': {'id': '1', 'title': 'test',
                              'content': 'abc', 'source': 'x',
                              'published_at': '2024-01-01'}}]
    with patch.object(client._client, 'search', new=AsyncMock(return_value={'hits': {'hits': fake_hits}})):
        result = await client.search_news(query='test')
        assert isinstance(result, list)
        assert result[0]['title'] == 'test'


@pytest.mark.asyncio
async def test_search_empty():
    client = AsyncElasticClient()
    with patch.object(client._client,
                      'search',
                      new=AsyncMock(return_value={'hits': {'hits': []}})):
        result = await client.search_news(query='notfound')
        assert result == []


@pytest.mark.asyncio
async def test_get_by_id_success():
    client = AsyncElasticClient()
    fake_doc = {'_source': {'id': '1', 'title': 'test', 'content': 'abc',
                            'source': 'x', 'published_at': '2024-01-01'}}
    with patch.object(client._client, 'get', new=AsyncMock(return_value=fake_doc)):
        result = await client.get_by_id('1')
        assert result['id'] == '1'


@pytest.mark.asyncio
async def test_get_by_id_not_found():
    from src.news_mcp_server.exceptions import ResourceException
    client = AsyncElasticClient()
    with patch.object(client._client,
                      'get',
                      new=AsyncMock(side_effect=ResourceException('not found'))):
        result = await client.get_by_id('not_exist')
        assert result == {}


# === 真实数据集成测试（需本地ES有数据） ===
@pytest.mark.asyncio
@pytest.mark.integration
async def test_real_search():
    client = AsyncElasticClient()
    # 假设 ES 中有 title 包含 "实验室" 的文档
    result = await client.search_news(query="实验室", max_results=2)
    print(result)
    assert isinstance(result, list)
    assert len(result) < 3
    # 允许为空，但如果有数据应有 title 字段
    if result:
        assert "title" in result[0]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_real_get_by_id():
    client = AsyncElasticClient()
    # 先查一个真实 id
    docs = await client.search_news(query="", max_results=1)
    if docs:
        news_id = docs[0].get("news_id")
        doc = await client.get_by_id(news_id)
        assert doc["news_id"] == news_id
        print(doc)
