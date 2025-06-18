from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class SearchNewsRequest(BaseModel):
    query: str = Field(description="查询词")
    max_results: int = Field(default=1, description="最多结果数量")
    source: Optional[str] = Field(default=None, description="数据源")
    date_from: Optional[str] = Field(default=None, description="发布日期起始时间")
    date_to: Optional[str] = None

class NewsBaseItem(BaseModel):
    model_config = ConfigDict(extra='allow')
    news_id: str
    title: str
    release_time: str = Field(None, description="The release time of the news item")

class NewsDetailItem(NewsBaseItem):
    content: Optional[str] = Field(default="", description="The content of the news item")
    source: Optional[str] = Field(None, description="The source of the news item")
