import asyncio
import json
import logging
import os
import shutil
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Set

from .database import init_db, get_db


def check_system_dependencies():
    """Check if required system tools are installed."""
    missing = []

    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if not shutil.which("ffprobe"):
        missing.append("ffprobe")
    if not shutil.which("mkvmerge"):
        missing.append("mkvmerge (mkvtoolnix)")

    if missing:
        print("\n" + "=" * 60)
        print("ERROR: Missing required system dependencies!")
        print("=" * 60)
        print(f"\nMissing tools: {', '.join(missing)}")
        print("\nPlease install them:")
        print("  macOS:   brew install ffmpeg mkvtoolnix")
        print("  Ubuntu:  sudo apt install ffmpeg mkvtoolnix")
        print("  Windows: Download from official websites")
        print("=" * 60 + "\n")
        sys.exit(1)


# Check dependencies on import
check_system_dependencies()
from .routers import tasks, files, settings, watchers
from .services.queue import task_queue
from .services.watcher import directory_watcher
from .services.translator import process_mkv_translation, translate_subtitle_file
from .config import settings as app_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# WebSocket connections
ws_connections: Set[WebSocket] = set()


async def broadcast_progress(task_id: int, progress: int):
    """Broadcast progress update to all connected WebSocket clients."""
    message = json.dumps({"type": "progress", "task_id": task_id, "progress": progress})

    disconnected = set()
    for ws in ws_connections:
        try:
            await ws.send_text(message)
        except:
            disconnected.add(ws)

    ws_connections.difference_update(disconnected)


async def broadcast_task_update(task_id: int, status: str):
    """Broadcast task status update to all connected WebSocket clients."""
    message = json.dumps({"type": "status", "task_id": task_id, "status": status})

    disconnected = set()
    for ws in ws_connections:
        try:
            await ws.send_text(message)
        except:
            disconnected.add(ws)

    ws_connections.difference_update(disconnected)


async def process_task(task_id: int):
    """Process a single translation task."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        )
        task = await cursor.fetchone()

        if task is None:
            logger.error(f"Task {task_id} not found")
            return

    async def get_status() -> str | None:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT status FROM tasks WHERE id = ?",
                (task_id,),
            )
            row = await cursor.fetchone()
            return row["status"] if row else None

    file_path = task["file_path"]
    file_ext = os.path.splitext(file_path)[1].lower()
    target_language = task["target_language"]
    llm_provider = task["llm_provider"]
    subtitle_track = task["subtitle_track"]
    force_override = bool(task["force_override"]) if task["force_override"] is not None else False

    async def get_output_settings() -> tuple[str, bool]:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT key, value FROM app_settings WHERE key IN (?, ?)",
                ("subtitle_output_format", "overwrite_mkv"),
            )
            rows = await cursor.fetchall()
            stored = {row["key"]: row["value"] for row in rows}

        output_format = stored.get(
            "subtitle_output_format", app_settings.subtitle_output_format
        )
        overwrite_value = stored.get("overwrite_mkv", app_settings.overwrite_mkv)

        def parse_bool(value) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)

        overwrite_mkv = parse_bool(overwrite_value)

        if output_format not in ("mkv", "srt", "ass"):
            output_format = "mkv"
        if overwrite_mkv:
            output_format = "mkv"
        elif output_format in ("srt", "ass"):
            overwrite_mkv = False

        return output_format, overwrite_mkv

    async def progress_callback(progress: int):
        await task_queue.update_progress(task_id, progress)
        await broadcast_progress(task_id, progress)

    async def should_skip(output_format: str, overwrite_mkv: bool) -> bool:
        from .services import subtitle as subtitle_service

        # If force_override is enabled, never skip
        if force_override:
            return False

        if file_ext in [".srt", ".ass"]:
            if output_format not in ["srt", "ass"]:
                return False
            base, _ = os.path.splitext(file_path)
            lang_tag = subtitle_service.get_language_tag(target_language)
            output_path = f"{base}.{lang_tag}.{output_format}"
            return os.path.exists(output_path)

        base, ext = os.path.splitext(file_path)
        if output_format in ("srt", "ass"):
            lang_tag = subtitle_service.get_language_tag(target_language)
            output_path = f"{base}.{lang_tag}.{output_format}"
            return os.path.exists(output_path)

        lang_code = subtitle_service.get_language_code(target_language)
        info = await subtitle_service.get_subtitle_tracks(file_path)
        for track in info.tracks:
            if track.language and track.language.lower() == lang_code:
                return True

        if not overwrite_mkv:
            output_path = f"{base}.translated{ext}"
            return os.path.exists(output_path)

        return False

    try:
        output_format, overwrite_mkv = await get_output_settings()
        if await should_skip(output_format, overwrite_mkv):
            logger.info(
                "Task %s skipped because target output already exists",
                task_id,
            )
            await task_queue.update_progress(task_id, 100)
            await broadcast_task_update(task_id, "completed")
            return
        await broadcast_task_update(task_id, "processing")
        if file_ext in [".srt", ".ass"]:
            # For subtitle inputs, automatically use appropriate output format
            if output_format not in ["srt", "ass"]:
                # Default to same format as input, or ass if input is srt
                output_format = file_ext[1:]  # Remove the dot: ".ass" -> "ass"

            base, _ = os.path.splitext(file_path)
            from .services import subtitle as subtitle_service
            lang_tag = subtitle_service.get_language_tag(target_language)
            output_path = f"{base}.{lang_tag}.{output_format}"

            output_path = await translate_subtitle_file(
                subtitle_path=file_path,
                output_path=output_path,
                llm_provider=llm_provider,
                source_language=app_settings.source_language,
                target_language=target_language,
                bilingual=app_settings.bilingual_output,
                output_format=output_format,
                progress_callback=progress_callback,
            )
        else:
            output_path = await process_mkv_translation(
                mkv_path=file_path,
                target_language=target_language,
                llm_provider=llm_provider,
                subtitle_track=subtitle_track,
                source_language=app_settings.source_language,
                bilingual=app_settings.bilingual_output,
                output_format=output_format,
                overwrite=overwrite_mkv,
                progress_callback=progress_callback,
            )

        logger.info(f"Task {task_id} completed: {output_path}")
        status = await get_status()
        if status != "cancelled":
            # Record the completed translation in database
            async with get_db() as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO translated_files (file_path, target_language, output_path)
                    VALUES (?, ?, ?)
                    """,
                    (file_path, target_language, output_path),
                )
                await db.commit()
            await broadcast_task_update(task_id, "completed")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        status = await get_status()
        if status != "cancelled":
            await broadcast_task_update(task_id, "failed")
            raise


async def check_file_should_skip(db, file_path: str, target_language: str) -> tuple[bool, str]:
    """Check if a file should be skipped for translation."""
    from .models.task import TaskStatus
    from .services import subtitle as subtitle_service

    # 1. Check if there's already a pending/processing task
    cursor = await db.execute(
        """
        SELECT id, status FROM tasks
        WHERE file_path = ? AND target_language = ? AND status IN (?, ?)
        """,
        (file_path, target_language, TaskStatus.PENDING.value, TaskStatus.PROCESSING.value),
    )
    existing_task = await cursor.fetchone()
    if existing_task:
        return True, f"Task exists (id={existing_task['id']})"

    # 2. Check if already translated in database
    cursor = await db.execute(
        "SELECT id FROM translated_files WHERE file_path = ? AND target_language = ?",
        (file_path, target_language),
    )
    if await cursor.fetchone():
        return True, "Already translated"

    # 3. For MKV, check if target language subtitle track exists
    if file_path.lower().endswith(".mkv"):
        try:
            lang_code = subtitle_service.get_language_code(target_language)
            info = await subtitle_service.get_subtitle_tracks(file_path)
            for track in info.tracks:
                if track.language and track.language.lower() == lang_code:
                    return True, f"MKV has {target_language} track"
        except Exception:
            pass

    # 4. Check if output file exists
    base, ext = os.path.splitext(file_path)
    lang_tag = subtitle_service.get_language_tag(target_language)
    for fmt in ["srt", "ass"]:
        if os.path.exists(f"{base}.{lang_tag}.{fmt}"):
            return True, "Output file exists"
    if os.path.exists(f"{base}.translated{ext}"):
        return True, "Translated file exists"

    return False, ""


async def on_new_file_detected(
    file_path: str, target_language: str, llm_provider: str
):
    """Handler for new files detected by directory watcher."""
    file_name = os.path.basename(file_path)

    async with get_db() as db:
        # Check if file should be skipped
        should_skip, reason = await check_file_should_skip(db, file_path, target_language)
        if should_skip:
            logger.debug(f"Skipped {file_path}: {reason}")
            return

        cursor = await db.execute(
            """
            INSERT INTO tasks (file_path, file_name, target_language, llm_provider)
            VALUES (?, ?, ?, ?)
            """,
            (file_path, file_name, target_language, llm_provider),
        )
        await db.commit()

        task_id = cursor.lastrowid
        logger.info(f"Auto-created task {task_id} for {file_path}")

        # Broadcast new task
        message = json.dumps({"type": "new_task", "task_id": task_id})
        for ws in ws_connections:
            try:
                await ws.send_text(message)
            except:
                pass


async def init_watchers(scan_existing: bool = True):
    """Initialize watchers from database and optionally scan existing files."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM watchers WHERE enabled = 1"
        )
        rows = await cursor.fetchall()

        for row in rows:
            try:
                directory_watcher.start_watching(
                    row["id"],
                    row["path"],
                    row["target_language"],
                    row["llm_provider"],
                )

                # Scan existing files in the directory
                if scan_existing:
                    logger.info(f"Scanning existing files in {row['path']}...")
                    stats = await directory_watcher.scan_directory(
                        row["path"],
                        row["target_language"],
                        row["llm_provider"],
                    )
                    logger.info(
                        f"Watcher {row['id']}: scanned {stats['scanned']} files, "
                        f"created {stats['triggered']} tasks"
                    )
            except Exception as e:
                logger.error(f"Failed to start watcher {row['id']}: {e}")


async def load_settings_from_db():
    """Load settings from database on startup."""
    async with get_db() as db:
        cursor = await db.execute("SELECT key, value FROM app_settings")
        rows = await cursor.fetchall()

        for row in rows:
            key, value = row["key"], row["value"]
            if hasattr(app_settings, key):
                current_type = type(getattr(app_settings, key))
                if current_type == bool:
                    setattr(app_settings, key, value.lower() in ("true", "1", "yes") if isinstance(value, str) else bool(value))
                elif current_type == int:
                    setattr(app_settings, key, int(value))
                else:
                    setattr(app_settings, key, value)

        logger.info("Loaded settings from database")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting SubAutoTrans...")

    # Initialize database
    await init_db()

    # Load settings from database
    await load_settings_from_db()

    # Configure task queue
    task_queue.set_task_handler(process_task)
    task_queue.set_max_concurrent(app_settings.max_concurrent_tasks)
    await task_queue.start()

    # Configure directory watcher
    directory_watcher.set_new_file_callback(on_new_file_detected)
    await init_watchers()

    logger.info("SubAutoTrans started successfully")

    yield

    # Shutdown
    logger.info("Shutting down SubAutoTrans...")
    await task_queue.stop()
    directory_watcher.stop_all()
    logger.info("SubAutoTrans stopped")


# Create FastAPI app
app = FastAPI(
    title="SubAutoTrans",
    description="Subtitle Translation Service",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tasks.router)
app.include_router(files.router)
app.include_router(settings.router)
app.include_router(watchers.router)


@app.get("/api")
async def api_info():
    """API info endpoint."""
    return {
        "name": "SubAutoTrans",
        "version": "1.0.0",
        "description": "Subtitle Translation Service",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket):
    """WebSocket endpoint for real-time progress updates."""
    await websocket.accept()
    ws_connections.add(websocket)

    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_connections.discard(websocket)
    except Exception:
        ws_connections.discard(websocket)


# Serve frontend static files (for Docker deployment)
STATIC_DIR = Path(__file__).parent.parent / "static"

if STATIC_DIR.exists():
    # Mount static assets (js, css, images, etc.)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/")
    async def serve_index():
        """Serve the index.html for root path."""
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes."""
        # Check if the file exists in static directory
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Return index.html for SPA routing
        return FileResponse(STATIC_DIR / "index.html")
