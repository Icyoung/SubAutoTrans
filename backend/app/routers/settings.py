from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..services.queue import task_queue
from ..config import settings
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import json

router = APIRouter(prefix="/api/settings", tags=["settings"])


class AppSettings(BaseModel):
    # LLM settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_base_url: Optional[str] = None
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-3-sonnet-20240229"
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: Optional[str] = None
    glm_api_key: Optional[str] = None
    glm_model: str = "glm-4.6"
    glm_base_url: Optional[str] = None
    default_llm: str = "openai"

    # Translation settings
    target_language: str = "Chinese"
    source_language: str = "auto"
    bilingual_output: bool = False
    subtitle_output_format: str = "mkv"
    overwrite_mkv: bool = False

    # Queue settings
    max_concurrent_tasks: int = 2


class SettingsUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    openai_base_url: Optional[str] = None
    claude_api_key: Optional[str] = None
    claude_model: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    deepseek_model: Optional[str] = None
    deepseek_base_url: Optional[str] = None
    glm_api_key: Optional[str] = None
    glm_model: Optional[str] = None
    glm_base_url: Optional[str] = None
    default_llm: Optional[str] = None
    target_language: Optional[str] = None
    source_language: Optional[str] = None
    bilingual_output: Optional[bool] = None
    subtitle_output_format: Optional[str] = None
    overwrite_mkv: Optional[bool] = None
    max_concurrent_tasks: Optional[int] = None


class LLMTestRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None


@router.get("", response_model=AppSettings)
async def get_settings():
    """Get application settings."""
    async with get_db() as db:
        cursor = await db.execute("SELECT key, value FROM app_settings")
        rows = await cursor.fetchall()

        stored_settings = {row["key"]: row["value"] for row in rows}

    # Merge with defaults from config
    return AppSettings(
        openai_api_key=_mask_key(
            stored_settings.get("openai_api_key", settings.openai_api_key)
        ),
        openai_model=stored_settings.get("openai_model", settings.openai_model),
        openai_base_url=stored_settings.get(
            "openai_base_url", settings.openai_base_url
        ),
        claude_api_key=_mask_key(
            stored_settings.get("claude_api_key", settings.claude_api_key)
        ),
        claude_model=stored_settings.get("claude_model", settings.claude_model),
        deepseek_api_key=_mask_key(
            stored_settings.get("deepseek_api_key", settings.deepseek_api_key)
        ),
        deepseek_model=stored_settings.get(
            "deepseek_model", settings.deepseek_model
        ),
        deepseek_base_url=stored_settings.get(
            "deepseek_base_url", settings.deepseek_base_url
        ),
        glm_api_key=_mask_key(
            stored_settings.get("glm_api_key", settings.glm_api_key)
        ),
        glm_model=stored_settings.get("glm_model", settings.glm_model),
        glm_base_url=stored_settings.get(
            "glm_base_url", settings.glm_base_url
        ),
        default_llm=stored_settings.get("default_llm", settings.default_llm),
        target_language=stored_settings.get(
            "target_language", settings.target_language
        ),
        source_language=stored_settings.get(
            "source_language", settings.source_language
        ),
        bilingual_output=_parse_bool(
            stored_settings.get("bilingual_output", settings.bilingual_output)
        ),
        subtitle_output_format=stored_settings.get(
            "subtitle_output_format", settings.subtitle_output_format
        ),
        overwrite_mkv=_parse_bool(
            stored_settings.get("overwrite_mkv", settings.overwrite_mkv)
        ),
        max_concurrent_tasks=int(
            stored_settings.get(
                "max_concurrent_tasks", settings.max_concurrent_tasks
            )
        ),
    )


@router.put("", response_model=AppSettings)
async def update_settings(update: SettingsUpdate):
    """Update application settings."""
    async with get_db() as db:
        for key, value in update.model_dump(exclude_none=True).items():
            # Don't store if value is masked
            if key.endswith("_api_key") and isinstance(value, str):
                if value == "***" or "..." in value:
                    continue

            str_value = str(value) if not isinstance(value, str) else value

            await db.execute(
                """
                INSERT INTO app_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = ?
                """,
                (key, str_value, str_value),
            )

        await db.commit()

    # Update runtime settings
    await _update_runtime_settings()
    task_queue.set_max_concurrent(settings.max_concurrent_tasks)
    await _normalize_output_settings()

    return await get_settings()


@router.get("/llm-providers")
async def get_llm_providers():
    """Get available LLM providers."""
    return {
        "providers": [
            {
                "id": "openai",
                "name": "OpenAI",
                "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            },
            {
                "id": "claude",
                "name": "Claude",
                "models": [
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307",
                ],
            },
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "models": ["deepseek-chat", "DeepSeek-V3.2", "deepseek-reasoner"],
            },
            {
                "id": "glm",
                "name": "GLM",
                "models": ["glm-4.6"],
            },
        ]
    }


@router.post("/test-llm")
async def test_llm_connection(request: LLMTestRequest):
    """Test LLM provider connection with a lightweight prompt."""
    async with get_db() as db:
        cursor = await db.execute("SELECT key, value FROM app_settings")
        rows = await cursor.fetchall()
        stored_settings = {row["key"]: row["value"] for row in rows}

    def _is_masked(value: Optional[str]) -> bool:
        return not value or value == "***" or "..." in value

    def _resolve(value: Optional[str], key: str, default: Optional[str]):
        if _is_masked(value):
            return stored_settings.get(key, default)
        return value

    provider = request.provider.lower()

    if provider == "openai":
        api_key = _resolve(request.api_key, "openai_api_key", settings.openai_api_key)
        model = _resolve(request.model, "openai_model", settings.openai_model)
        base_url = _resolve(
            request.base_url, "openai_base_url", settings.openai_base_url
        )
    elif provider == "deepseek":
        api_key = _resolve(
            request.api_key, "deepseek_api_key", settings.deepseek_api_key
        )
        model = _resolve(request.model, "deepseek_model", settings.deepseek_model)
        base_url = _resolve(
            request.base_url, "deepseek_base_url", settings.deepseek_base_url
        )
    elif provider == "glm":
        api_key = _resolve(request.api_key, "glm_api_key", settings.glm_api_key)
        model = _resolve(request.model, "glm_model", settings.glm_model)
        base_url = _resolve(request.base_url, "glm_base_url", settings.glm_base_url)
    elif provider == "claude":
        api_key = _resolve(
            request.api_key, "claude_api_key", settings.claude_api_key
        )
        model = _resolve(request.model, "claude_model", settings.claude_model)
        base_url = None
    else:
        raise HTTPException(status_code=400, detail="Unknown provider")

    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    try:
        if provider == "claude":
            client = AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model=model,
                max_tokens=8,
                messages=[{"role": "user", "content": "Reply with ok."}],
                system="You are a helpful assistant.",
            )
            if not response.content:
                raise RuntimeError("Empty response from Claude")
        else:
            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            client = AsyncOpenAI(**client_kwargs)
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Reply with ok."},
                ],
                max_tokens=8,
                temperature=0,
            )
            if not response.choices:
                raise RuntimeError("Empty response from provider")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok"}


@router.get("/languages")
async def get_languages():
    """Get available languages."""
    return {
        "languages": [
            {"code": "Chinese", "name": "Chinese (Simplified)"},
            {"code": "English", "name": "English"},
            {"code": "Japanese", "name": "Japanese"},
            {"code": "Korean", "name": "Korean"},
            {"code": "French", "name": "French"},
            {"code": "German", "name": "German"},
            {"code": "Spanish", "name": "Spanish"},
            {"code": "Russian", "name": "Russian"},
            {"code": "Portuguese", "name": "Portuguese"},
            {"code": "Italian", "name": "Italian"},
        ]
    }


def _mask_key(key: Optional[str]) -> Optional[str]:
    """Mask API key for display."""
    if not key:
        return None
    if len(key) <= 8:
        return "***"
    return f"{key[:3]}...{key[-4:]}"


def _parse_bool(value) -> bool:
    """Parse boolean from various types."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


async def _update_runtime_settings():
    """Update runtime settings from database."""
    async with get_db() as db:
        cursor = await db.execute("SELECT key, value FROM app_settings")
        rows = await cursor.fetchall()

        for row in rows:
            key, value = row["key"], row["value"]

            if hasattr(settings, key):
                current_type = type(getattr(settings, key))
                if current_type == bool:
                    setattr(settings, key, _parse_bool(value))
                elif current_type == int:
                    setattr(settings, key, int(value))
                else:
                    setattr(settings, key, value)


async def _normalize_output_settings():
    """Keep output settings mutually exclusive and persist adjustments."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT key, value FROM app_settings WHERE key IN (?, ?)",
            ("subtitle_output_format", "overwrite_mkv"),
        )
        rows = await cursor.fetchall()
        stored = {row["key"]: row["value"] for row in rows}

    output_format = stored.get("subtitle_output_format", settings.subtitle_output_format)
    overwrite_mkv = _parse_bool(
        stored.get("overwrite_mkv", settings.overwrite_mkv)
    )

    if output_format not in ("mkv", "srt", "ass"):
        output_format = "mkv"

    if overwrite_mkv:
        output_format = "mkv"
    elif output_format in ("srt", "ass"):
        overwrite_mkv = False

    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO app_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?
            """,
            ("subtitle_output_format", output_format, output_format),
        )
        await db.execute(
            """
            INSERT INTO app_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?
            """,
            ("overwrite_mkv", str(overwrite_mkv), str(overwrite_mkv)),
        )
        await db.commit()

    settings.subtitle_output_format = output_format
    settings.overwrite_mkv = overwrite_mkv
