from abc import ABC, abstractmethod
from typing import AsyncIterator
from dataclasses import dataclass


@dataclass
class TranslationResult:
    original: str
    translated: str
    tokens_used: int = 0


class BaseLLM(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """Translate text from source to target language."""
        pass

    @abstractmethod
    async def translate_batch(
        self,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[str]:
        """Translate a batch of texts."""
        pass

    def _build_translation_prompt(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """Build the translation prompt."""
        source_str = (
            f"from {source_language}" if source_language != "auto" else ""
        )
        return f"""Translate the following subtitle text {source_str} to {target_language}.

Rules:
1. Keep the translation natural and fluent
2. Preserve the original meaning and tone
3. Keep any formatting tags like {{\\an8}} or {{\\pos(x,y)}}
4. Do not add any explanations, only output the translation
5. If there are multiple lines, translate each line and keep the line structure

Text to translate:
{text}

Translation:"""

    def _build_batch_translation_prompt(
        self,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> str:
        """Build prompt for batch translation."""
        source_str = (
            f"from {source_language}" if source_language != "auto" else ""
        )
        numbered_texts = "\n".join(
            f"[{i+1}] {text}" for i, text in enumerate(texts)
        )

        return f"""Translate the following subtitle lines {source_str} to {target_language}.

Rules:
1. Keep translations natural and fluent
2. Preserve the original meaning and tone
3. Keep any formatting tags like {{\\an8}} or {{\\pos(x,y)}}
4. Output ONLY the translations, one per line, with the same numbering format [n]
5. Do not add any explanations

Lines to translate:
{numbered_texts}

Translations:"""
