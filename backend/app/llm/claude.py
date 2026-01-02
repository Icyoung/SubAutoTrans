import re
from anthropic import AsyncAnthropic
from .base import BaseLLM
from ..config import settings


class ClaudeLLM(BaseLLM):
    """Claude LLM provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or settings.claude_api_key
        self.model = model or settings.claude_model
        self.client = AsyncAnthropic(api_key=self.api_key)

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """Translate text using Claude."""
        prompt = self._build_translation_prompt(
            text, source_language, target_language
        )

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            system="You are a professional subtitle translator. "
            "Translate accurately while maintaining natural flow.",
        )

        return response.content[0].text.strip()

    async def translate_batch(
        self,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[str]:
        """Translate a batch of texts using Claude."""
        if not texts:
            return []

        prompt = self._build_batch_translation_prompt(
            texts, source_language, target_language
        )

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            system="You are a professional subtitle translator. "
            "Translate accurately while maintaining natural flow.",
        )

        result_text = response.content[0].text.strip()
        return self._parse_batch_response(result_text, len(texts))

    def _parse_batch_response(
        self, response: str, expected_count: int
    ) -> list[str]:
        """Parse the batch translation response."""
        lines = response.strip().split("\n")
        translations = []

        pattern = re.compile(r"^\[(\d+)\]\s*(.*)$")

        for line in lines:
            match = pattern.match(line.strip())
            if match:
                translations.append(match.group(2))
            elif line.strip() and not line.startswith("["):
                translations.append(line.strip())

        while len(translations) < expected_count:
            translations.append("")

        return translations[:expected_count]
