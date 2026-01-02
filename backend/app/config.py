from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # LLM - OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    openai_base_url: Optional[str] = None

    # LLM - Claude
    claude_api_key: str = ""
    claude_model: str = "claude-3-sonnet-20240229"

    # LLM - DeepSeek (OpenAI-compatible)
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: Optional[str] = "https://api.deepseek.com"

    # LLM - GLM (OpenAI-compatible)
    glm_api_key: str = ""
    glm_model: str = "glm-4.6"
    glm_base_url: Optional[str] = "https://open.bigmodel.cn/api/paas/v4"

    # Default LLM provider
    default_llm: str = "openai"

    # Translation settings
    target_language: str = "Chinese"
    source_language: str = "auto"
    bilingual_output: bool = False
    subtitle_output_format: str = "mkv"  # mkv | srt | ass
    overwrite_mkv: bool = False

    # Output settings
    keep_original_subtitle: bool = True

    # Queue settings
    max_concurrent_tasks: int = 2
    retry_count: int = 3

    # Directories
    temp_dir: str = Field(default="./data/temp")
    output_dir: str = ""  # Empty means output in place

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/tasks.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
os.makedirs(settings.temp_dir, exist_ok=True)
os.makedirs("./data", exist_ok=True)
