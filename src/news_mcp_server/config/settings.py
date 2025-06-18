import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

class ApplicationSettings(BaseModel):
    CORS_ORIGINS: list = ["*"]
    CORS_METHODS: list = ["GET", "POST", "OPTIONS"]
    CORS_HEADERS: list = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    API_KEY: str | None = os.getenv("NEWS_MCP_API_KEY")
    SESSION_SECREY_KEY: str = os.getenv("SESSION_SECREY_KEY")
    TRANSPORT: str = "streamable-http"


class ElasticSearchSettings(BaseModel):
    ES_HOST: str = os.getenv("ES_HOST")
    ES_PORT: int = Field(default=os.getenv("ES_PORT"), le=1, ge=65535)
    ES_INDEX: str = os.getenv("ES_INDEX")
    URL: str = os.getenv("ES_HOST")
    MAX_RESULTS_LIMIT: int = 100


    @property
    def api_key(self) -> str:
        es_api_key =  os.getenv("ES_API_KEY")
        if es_api_key is None:
            raise Exception("es apy key should be provided")
        return es_api_key


es_settings = ElasticSearchSettings()
app_settings = ApplicationSettings()
print(es_settings.ES_HOST)