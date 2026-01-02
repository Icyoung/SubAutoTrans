import asyncio
import json
import os
import tempfile
from copy import deepcopy
from typing import Optional
from dataclasses import dataclass
import pysubs2
import logging
import chardet

logger = logging.getLogger(__name__)


@dataclass
class SubtitleTrack:
    index: int
    codec: str
    language: Optional[str]
    title: Optional[str]


@dataclass
class SubtitleInfo:
    file_path: str
    tracks: list[SubtitleTrack]


async def run_command(cmd: list[str]) -> tuple[int, str, str]:
    """Run a command asynchronously."""
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return process.returncode, stdout.decode(), stderr.decode()


async def get_subtitle_tracks(file_path: str) -> SubtitleInfo:
    """Get subtitle tracks from an MKV file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "s",
        file_path,
    ]

    returncode, stdout, stderr = await run_command(cmd)

    if returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr}")

    data = json.loads(stdout)
    tracks = []

    for stream in data.get("streams", []):
        track = SubtitleTrack(
            index=stream.get("index", 0),
            codec=stream.get("codec_name", "unknown"),
            language=stream.get("tags", {}).get("language"),
            title=stream.get("tags", {}).get("title"),
        )
        tracks.append(track)

    return SubtitleInfo(file_path=file_path, tracks=tracks)


async def extract_subtitle(
    file_path: str,
    track_index: int,
    output_path: Optional[str] = None,
) -> str:
    """Extract a subtitle track from an MKV file."""
    if output_path is None:
        output_path = tempfile.mktemp(suffix=".srt")

    # Get track info to determine codec
    info = await get_subtitle_tracks(file_path)
    track = next((t for t in info.tracks if t.index == track_index), None)

    if track is None:
        raise ValueError(f"Subtitle track {track_index} not found")

    # Map stream index to subtitle stream index
    subtitle_stream_index = 0
    for t in info.tracks:
        if t.index == track_index:
            break
        subtitle_stream_index += 1

    # PGS subtitles (hdmv_pgs_subtitle) cannot be extracted as text
    if track.codec in ["hdmv_pgs_subtitle", "dvd_subtitle"]:
        raise ValueError(
            f"Subtitle track {track_index} is a graphical subtitle ({track.codec}), "
            "text extraction not supported"
        )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", file_path,
        "-map", f"0:s:{subtitle_stream_index}",
        "-c:s", "srt",
        output_path,
    ]

    returncode, stdout, stderr = await run_command(cmd)

    if returncode != 0:
        raise RuntimeError(f"ffmpeg extraction failed: {stderr}")

    return output_path


async def mux_subtitle(
    video_path: str,
    subtitle_path: str,
    output_path: str,
    language: str = "chi",
    track_name: Optional[str] = None,
) -> str:
    """Mux a subtitle file into an MKV file using mkvmerge."""
    if track_name is None:
        track_name = f"Translated ({language})"

    cmd = [
        "mkvmerge",
        "-o", output_path,
        video_path,
        "--language", f"0:{language}",
        "--track-name", f"0:{track_name}",
        subtitle_path,
    ]

    returncode, stdout, stderr = await run_command(cmd)

    if returncode not in [0, 1]:  # mkvmerge returns 1 for warnings
        raise RuntimeError(f"mkvmerge failed: {stderr}")

    return output_path


def detect_encoding(file_path: str) -> str:
    """Detect file encoding using chardet."""
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    encoding = result.get('encoding', 'utf-8')
    # Handle common encoding aliases
    if encoding and encoding.lower() in ['utf-16', 'utf-16le', 'utf-16be']:
        return encoding
    return encoding or 'utf-8'


def parse_subtitle(file_path: str) -> pysubs2.SSAFile:
    """Parse a subtitle file with automatic encoding detection."""
    encoding = detect_encoding(file_path)
    logger.info(f"Detected encoding for {file_path}: {encoding}")
    return pysubs2.load(file_path, encoding=encoding)


def save_subtitle(subs: pysubs2.SSAFile, file_path: str):
    """Save a subtitle file."""
    subs.save(file_path)


def create_bilingual_subtitle(
    original: pysubs2.SSAFile,
    translated: pysubs2.SSAFile,
    output_format: Optional[str] = None,
) -> pysubs2.SSAFile:
    """Create a bilingual subtitle by combining original and translated."""
    bilingual = pysubs2.SSAFile()

    base_size = None
    if output_format == "ass":
        default_style = original.styles.get("Default")
        if default_style:
            base_size = int(default_style.fontsize)
        else:
            base_size = 20
        smaller_size = max(10, int(base_size * 0.8))

    for orig_event, trans_event in zip(original.events, translated.events):
        new_event = deepcopy(orig_event)
        if output_format == "ass" and base_size:
            new_event.text = (
                f"{trans_event.text}\\N{{\\fs{smaller_size}}}"
                f"{orig_event.text}{{\\r}}"
            )
        else:
            new_event.text = f"{trans_event.text}\\N{orig_event.text}"
        bilingual.events.append(new_event)

    return bilingual


def get_language_code(language: str) -> str:
    """Convert language name to ISO 639-2 code."""
    language_map = {
        "chinese": "chi",
        "english": "eng",
        "japanese": "jpn",
        "korean": "kor",
        "french": "fre",
        "german": "ger",
        "spanish": "spa",
        "russian": "rus",
        "portuguese": "por",
        "italian": "ita",
    }
    return language_map.get(language.lower(), "und")


def get_language_tag(language: str) -> str:
    """Convert language name to a filename-friendly tag."""
    tag_map = {
        "chinese": "zh-Hans",
        "english": "en",
        "japanese": "ja",
        "korean": "ko",
        "french": "fr",
        "german": "de",
        "spanish": "es",
        "russian": "ru",
        "portuguese": "pt",
        "italian": "it",
    }
    return tag_map.get(language.lower(), "und")


def get_known_language_tags() -> list[str]:
    """Return known language tags used for output filenames."""
    return [
        "zh-Hans",
        "en",
        "ja",
        "ko",
        "fr",
        "de",
        "es",
        "ru",
        "pt",
        "it",
        "und",
    ]
