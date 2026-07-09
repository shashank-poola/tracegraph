"""Application settings loaded from environment / backend/.env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Server
    frontend_origin: str = "http://localhost:3000"
    log_level: str = "INFO"

    # LLM fallback chain: GLM 5.2 → Groq GPT-OSS → Gemini
    # 1) Z.AI / GLM (primary)
    zai_api_key: str = Field(default="", repr=False)
    zai_model: str = "glm-5.2"
    zai_base_url: str = "https://api.z.ai/api/paas/v4"

    # 2) Groq GPT-OSS (first fallback)
    groq_api_key: str = Field(default="", repr=False)
    groq_model: str = "openai/gpt-oss-120b"

    # 3) Gemini (second fallback)
    gemini_api_key: str = Field(default="", repr=False)
    gemini_model: str = "gemini-2.0-flash"

    llm_concurrency: int = 5
    llm_timeout_seconds: int = 120

    # Neo4j Aura — knowledge graph (empty = graph step skipped)
    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = Field(default="", repr=False)
    neo4j_database: str = "neo4j"

    # SQLite — job state + artifact cache (backend owns all persistence)
    sqlite_path: str = "data/tracegraph.db"

    # Crawl (Playwright)
    crawl_artifact_dir: str = "artifacts"
    crawl_headless: bool = True
    crawl_max_screens: int = 20
    crawl_nav_timeout_ms: int = 20_000

    # Repo analysis bounds
    max_python_files: int = 200
    max_file_bytes: int = 200_000

    # GitHub token arrives per-request, never stored in settings
    job_ttl_seconds: int = 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
