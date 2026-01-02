import os
import shutil
import tempfile
from copy import deepcopy
from typing import Callable, Awaitable, Optional
import pysubs2
from ..llm.base import BaseLLM
from ..llm.openai import OpenAILLM
from ..llm.claude import ClaudeLLM
from ..llm.deepseek import DeepSeekLLM
from ..llm.glm import GLMLLM
from ..config import settings
from . import subtitle as subtitle_service
import logging

logger = logging.getLogger(__name__)

# Batch size for translation
BATCH_SIZE = 20


def get_llm(provider: str) -> BaseLLM:
    """Get LLM instance by provider name."""
    if provider == "openai":
        return OpenAILLM()
    elif provider == "claude":
        return ClaudeLLM()
    elif provider == "deepseek":
        return DeepSeekLLM()
    elif provider == "glm":
        return GLMLLM()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


async def translate_subtitle_file(
    subtitle_path: str,
    output_path: str,
    llm_provider: str,
    source_language: str = "auto",
    target_language: str = "Chinese",
    bilingual: bool = False,
    output_format: Optional[str] = None,
    progress_callback: Optional[Callable[[int], Awaitable[None]]] = None,
) -> str:
    """Translate a subtitle file."""
    llm = get_llm(llm_provider)

    # Parse subtitle with encoding detection
    subs = subtitle_service.parse_subtitle(subtitle_path)
    total_events = len(subs.events)

    if total_events == 0:
        raise ValueError("Subtitle file is empty")

    logger.info(f"Translating {total_events} subtitle lines")

    # Translate in batches
    translated_texts = []

    for i in range(0, total_events, BATCH_SIZE):
        batch = subs.events[i : i + BATCH_SIZE]
        texts = [event.text for event in batch]

        try:
            batch_translated = await llm.translate_batch(
                texts, source_language, target_language
            )
            translated_texts.extend(batch_translated)
        except Exception as e:
            logger.error(f"Batch translation failed: {e}")
            # Fallback to single translation
            for text in texts:
                try:
                    translated = await llm.translate(
                        text, source_language, target_language
                    )
                    translated_texts.append(translated)
                except Exception as e2:
                    logger.error(f"Single translation failed: {e2}")
                    translated_texts.append(text)  # Keep original on failure

        # Update progress
        if progress_callback:
            progress = int((len(translated_texts) / total_events) * 80) + 10
            await progress_callback(min(progress, 90))

    # Create translated subtitle
    translated_subs = deepcopy(subs)
    for i, event in enumerate(translated_subs.events):
        if i < len(translated_texts):
            event.text = translated_texts[i]

    if bilingual:
        # Create bilingual subtitle
        translated_subs = subtitle_service.create_bilingual_subtitle(
            subs, translated_subs, output_format=output_format
        )

    # Save translated subtitle
    translated_subs.save(output_path)
    logger.info(f"Translated subtitle saved to {output_path}")

    return output_path


async def process_mkv_translation(
    mkv_path: str,
    target_language: str,
    llm_provider: str,
    subtitle_track: Optional[int] = None,
    source_language: str = "auto",
    bilingual: bool = False,
    output_format: str = "mkv",
    overwrite: bool = False,
    progress_callback: Optional[Callable[[int], Awaitable[None]]] = None,
) -> str:
    """Process full MKV translation workflow."""
    # Get subtitle tracks
    if progress_callback:
        await progress_callback(5)

    info = await subtitle_service.get_subtitle_tracks(mkv_path)

    if not info.tracks:
        raise ValueError("No subtitle tracks found in the file")

    # Select track
    if subtitle_track is None:
        # Use first text-based subtitle track
        for track in info.tracks:
            if track.codec not in ["hdmv_pgs_subtitle", "dvd_subtitle"]:
                subtitle_track = track.index
                break

        if subtitle_track is None:
            raise ValueError("No text-based subtitle tracks found")

    # Extract subtitle
    if progress_callback:
        await progress_callback(10)

    temp_subtitle = await subtitle_service.extract_subtitle(
        mkv_path, subtitle_track
    )

    try:
        # Translate subtitle
        temp_suffix = f".{output_format}" if output_format in ("srt", "ass") else ".srt"
        temp_translated = tempfile.mktemp(suffix=temp_suffix)

        await translate_subtitle_file(
            temp_subtitle,
            temp_translated,
            llm_provider,
            source_language,
            target_language,
            bilingual,
            output_format=output_format,
            progress_callback=progress_callback,
        )

        # Generate output path
        base, ext = os.path.splitext(mkv_path)

        if output_format in ("srt", "ass"):
            lang_tag = subtitle_service.get_language_tag(target_language)
            output_path = f"{base}.{lang_tag}.{output_format}"
            shutil.move(temp_translated, output_path)
            if progress_callback:
                await progress_callback(100)
            return output_path

        # Mux back into MKV
        if progress_callback:
            await progress_callback(95)

        output_path = mkv_path if overwrite else f"{base}.translated{ext}"
        mux_output = (
            tempfile.mktemp(suffix=ext) if overwrite else output_path
        )

        lang_code = subtitle_service.get_language_code(target_language)
        track_name = f"{target_language}" + (" (Bilingual)" if bilingual else "")

        await subtitle_service.mux_subtitle(
            mkv_path,
            temp_translated,
            mux_output,
            language=lang_code,
            track_name=track_name,
        )

        if overwrite:
            shutil.move(mux_output, output_path)
            old_translated = f"{base}.translated{ext}"
            if os.path.exists(old_translated):
                os.remove(old_translated)

        if progress_callback:
            await progress_callback(100)

        return output_path

    finally:
        # Cleanup temp files
        for f in [temp_subtitle, temp_translated]:
            if os.path.exists(f):
                os.remove(f)
