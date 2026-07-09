"""Application settings loaded from environment / backend/.env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    frontend_origin: str = "http://localhost:3000"
    log_level: str = "INFO"

    # GitHub OAuth (user login — distinct from GitHub App webhook)
    github_oauth_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("GITHUB_OAUTH_CLIENT_ID", "GITHUB_APP_CLIENT_ID"),
    )
    github_oauth_client_secret: str = Field(
        default="",
        repr=False,
        validation_alias=AliasChoices("GITHUB_OAUTH_CLIENT_SECRET", "GITHUB_APP_CLIENT_SECRET"),
    )
    github_oauth_callback_url: str = "http://localhost:8000/auth/github/callback"
    server_jwt_secret: str = Field(
        default="",
        repr=False,
        validation_alias=AliasChoices("SERVER_JWT_SECRET", "JWT_SECRET"),
    )
    session_ttl_seconds: int = 60 * 60 * 24 * 7
    oauth_cookie_secure: bool = False

    # LLM chain: GLM 5.2 → Groq GPT-OSS → Gemini
    zai_api_key: str = Field(default="", repr=False)
    zai_model: str = "glm-5.2"
    zai_base_url: str = "https://api.z.ai/api/paas/v4"
    groq_api_key: str = Field(default="", repr=False)
    groq_model: str = "openai/gpt-oss-120b"
    gemini_api_key: str = Field(default="", repr=False)
    gemini_model: str = "gemini-2.0-flash"
    llm_concurrency: int = 5
    llm_timeout_seconds: int = 120

    # Neo4j Aura
    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = Field(default="", repr=False)
    neo4j_database: str = "neo4j"
    neo4j_console_url: str = "https://console.neo4j.io"
    aura_instanceid: str = ""
    aura_instancename: str = ""

    # SQLite artifact store
    sqlite_path: str = "data/tracegraph.db"

    # GitHub App (webhook + PR comment write-back + install onboarding)
    github_app_id: str = ""
    github_app_slug: str = ""
    github_app_private_key_path: str = ""
    github_app_private_key: str = Field(default="", repr=False)
    github_webhook_secret: str = Field(default="", repr=False)

    # Crawl (Playwright)
    crawl_artifact_dir: str = "artifacts"
    crawl_headless: bool = True
    crawl_max_screens: int = 40
    crawl_nav_timeout_ms: int = 20_000
    crawl_llm_labeling: bool = True
    crawl_max_dom_bytes: int = 400_000

    # browser-use cloud agent (autonomous discovery — pairs with Playwright capture)
    browser_use_api_key: str = Field(default="", repr=False)
    crawl_browseruse_concurrency: int = 3
    crawl_agent_max_cost_usd: float = 2.0

    max_python_files: int = 200
    max_file_bytes: int = 200_000
    job_ttl_seconds: int = 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
