import re
from openai import AsyncOpenAI
from .base import BaseLLM
from ..config import settings


class OpenAILLM(BaseLLM):
    """OpenAI LLM provider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.base_url = base_url or settings.openai_base_url

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = AsyncOpenAI(**client_kwargs)

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> str:
        """Translate text using OpenAI."""
        prompt = self._build_translation_prompt(
            text, source_language, target_language
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional subtitle translator. "
                    "Translate accurately while maintaining natural flow.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    async def translate_batch(
        self,
        texts: list[str],
        source_language: str,
        target_language: str,
    ) -> list[str]:
        """Translate a batch of texts using OpenAI."""
        if not texts:
            return []

        prompt = self._build_batch_translation_prompt(
            texts, source_language, target_language
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional subtitle translator. "
                    "Translate accurately while maintaining natural flow.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        result_text = response.choices[0].message.content.strip()
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
                # Fallback: line without numbering
                translations.append(line.strip())

        # Ensure we have the expected number of translations
        while len(translations) < expected_count:
            translations.append("")

        return translations[:expected_count]
