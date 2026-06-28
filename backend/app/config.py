import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = os.environ.get("GROQ_API_KEY", "")
    github_token: str = os.environ.get("GITHUB_TOKEN", "")
    qdrant_url: str = os.environ.get("QDRANT_URL", "http://localhost:6333")


settings = Settings()