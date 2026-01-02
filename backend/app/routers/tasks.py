import os
import logging
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime
from ..database import get_db
from ..models.task import (
    TaskCreate,
    TaskResponse,
    TaskStatus,
    DirectoryTaskCreate,
    TaskIdList,
    TaskListResponse,
)
from ..services import subtitle as subtitle_service
from ..config import settings as app_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


async def check_file_should_skip(
    db, file_path: str, target_language: str, force_override: bool = False
) -> tuple[bool, str]:
    """
    Check if a file should be skipped for translation.
    Returns (should_skip, reason).
    """
    # If force_override is True, only check for existing pending/processing tasks
    # Skip all other checks (existing translations, subtitle tracks, output files)

    # 1. Check if there's already a pending/processing task for this file+language
    cursor = await db.execute(
        """
        SELECT id, status FROM tasks
        WHERE file_path = ? AND target_language = ? AND status IN (?, ?)
        """,
        (file_path, target_language, TaskStatus.PENDING.value, TaskStatus.PROCESSING.value),
    )
    existing_task = await cursor.fetchone()
    if existing_task:
        return True, f"Task already exists (id={existing_task['id']}, status={existing_task['status']})"

    # If force_override is True, skip all remaining checks
    if force_override:
        return False, ""

    # 2. Check if file is already marked as translated in database
    cursor = await db.execute(
        """
        SELECT id FROM translated_files WHERE file_path = ? AND target_language = ?
        """,
        (file_path, target_language),
    )
    if await cursor.fetchone():
        return True, "Already translated (recorded in database)"

    # 3. For MKV files, check if target language subtitle track already exists
    if file_path.lower().endswith(".mkv"):
        try:
            lang_code = subtitle_service.get_language_code(target_language)
            info = await subtitle_service.get_subtitle_tracks(file_path)
            for track in info.tracks:
                if track.language and track.language.lower() == lang_code:
                    return True, f"MKV already has {target_language} subtitle track"
        except Exception as e:
            logger.warning(f"Failed to check subtitle tracks for {file_path}: {e}")

    # 4. Check if output file already exists
    base, ext = os.path.splitext(file_path)
    lang_tag = subtitle_service.get_language_tag(target_language)

    # Check for subtitle output files
    for fmt in ["srt", "ass"]:
        output_path = f"{base}.{lang_tag}.{fmt}"
        if os.path.exists(output_path):
            return True, f"Output file already exists: {output_path}"

    # Check for translated MKV
    translated_mkv = f"{base}.translated{ext}"
    if os.path.exists(translated_mkv):
        return True, f"Translated file already exists: {translated_mkv}"

    return False, ""


@router.post("", response_model=TaskResponse)
async def create_task(task: TaskCreate):
    """Create a new translation task."""
    if not os.path.exists(task.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    if not task.file_path.lower().endswith((".mkv", ".srt", ".ass")):
        raise HTTPException(
            status_code=400,
            detail="File must be an MKV, SRT, or ASS file",
        )

    file_name = os.path.basename(task.file_path)

    async with get_db() as db:
        # Check if file should be skipped
        should_skip, reason = await check_file_should_skip(
            db, task.file_path, task.target_language, task.force_override
        )
        if should_skip:
            raise HTTPException(
                status_code=409,
                detail=f"File skipped: {reason}",
            )

        cursor = await db.execute(
            """
            INSERT INTO tasks (file_path, file_name, target_language, llm_provider, subtitle_track, force_override)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                task.file_path,
                file_name,
                task.target_language,
                task.llm_provider,
                task.subtitle_track if task.file_path.lower().endswith(".mkv") else None,
                1 if task.force_override else 0,
            ),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)
        )
        row = await cursor.fetchone()

        return _row_to_task(row)


@router.post("/directory")
async def create_directory_tasks(request: DirectoryTaskCreate):
    """Create tasks for all MKV files in a directory."""
    if not os.path.isdir(request.directory_path):
        raise HTTPException(status_code=404, detail="Directory not found")

    mkv_files = []

    def is_generated_subtitle(name: str) -> bool:
        lower_name = name.lower()
        if ".translated." in lower_name:
            return True
        if lower_name.endswith((".srt", ".ass")):
            for tag in subtitle_service.get_known_language_tags():
                if f".{tag.lower()}." in lower_name:
                    return True
        return False

    if request.recursive:
        for root, dirs, files in os.walk(request.directory_path):
            for f in files:
                if (
                    f.lower().endswith((".mkv", ".srt", ".ass"))
                    and not is_generated_subtitle(f)
                ):
                    mkv_files.append(os.path.join(root, f))
    else:
        for f in os.listdir(request.directory_path):
            if (
                f.lower().endswith((".mkv", ".srt", ".ass"))
                and not is_generated_subtitle(f)
            ):
                mkv_files.append(os.path.join(request.directory_path, f))

    if not mkv_files:
        raise HTTPException(
            status_code=404,
            detail="No MKV, SRT, or ASS files found in directory",
        )

    created_tasks = []
    skipped_files = []

    async with get_db() as db:
        for file_path in mkv_files:
            # Check if file should be skipped
            should_skip, reason = await check_file_should_skip(
                db, file_path, request.target_language, request.force_override
            )
            if should_skip:
                skipped_files.append({"file": file_path, "reason": reason})
                logger.info(f"Skipped {file_path}: {reason}")
                continue

            file_name = os.path.basename(file_path)

            cursor = await db.execute(
                """
                INSERT INTO tasks (file_path, file_name, target_language, llm_provider, force_override)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    file_path,
                    file_name,
                    request.target_language,
                    request.llm_provider,
                    1 if request.force_override else 0,
                ),
            )
            created_tasks.append(cursor.lastrowid)

        await db.commit()

    return {
        "created_count": len(created_tasks),
        "skipped_count": len(skipped_files),
        "task_ids": created_tasks,
        "skipped_files": skipped_files,
    }


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[TaskStatus] = None,
    limit: int = 20,
    offset: int = 0,
):
    """List all tasks with optional status filter and pagination."""
    async with get_db() as db:
        # Get total count
        if status:
            count_cursor = await db.execute(
                "SELECT COUNT(*) as count FROM tasks WHERE status = ?",
                (status.value,),
            )
        else:
            count_cursor = await db.execute("SELECT COUNT(*) as count FROM tasks")
        count_row = await count_cursor.fetchone()
        total = count_row["count"]

        # Get paginated tasks
        if status:
            cursor = await db.execute(
                """
                SELECT * FROM tasks WHERE status = ?
                ORDER BY created_at DESC LIMIT ? OFFSET ?
                """,
                (status.value, limit, offset),
            )
        else:
            cursor = await db.execute(
                """
                SELECT * FROM tasks
                ORDER BY created_at DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )

        rows = await cursor.fetchall()
        tasks = [_row_to_task(row) for row in rows]

        return TaskListResponse(
            tasks=tasks,
            total=total,
            limit=limit,
            offset=offset,
        )


@router.get("/stats")
async def get_task_stats():
    """Get task statistics."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT status, COUNT(*) as count FROM tasks GROUP BY status
            """
        )
        rows = await cursor.fetchall()

        stats = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "paused": 0,
            "total": 0,
        }

        for row in rows:
            stats[row["status"]] = row["count"]
            stats["total"] += row["count"]

        return stats


@router.post("/pause-all")
async def pause_all_tasks():
    """Pause all pending tasks."""
    async with get_db() as db:
        cursor = await db.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE status = ?",
            (TaskStatus.PAUSED.value, datetime.now().isoformat(), TaskStatus.PENDING.value),
        )
        await db.commit()

    return {"paused_count": cursor.rowcount}


@router.post("/pause-selected")
async def pause_selected_tasks(request: TaskIdList):
    """Pause selected pending tasks."""
    if not request.task_ids:
        raise HTTPException(status_code=400, detail="No task IDs provided")

    placeholders = ",".join("?" for _ in request.task_ids)
    async with get_db() as db:
        cursor = await db.execute(
            f"UPDATE tasks SET status = ?, updated_at = ? WHERE id IN ({placeholders}) AND status = ?",
            [TaskStatus.PAUSED.value, datetime.now().isoformat(), *request.task_ids, TaskStatus.PENDING.value],
        )
        await db.commit()

    return {"paused_count": cursor.rowcount}


@router.delete("/delete-all")
async def delete_all_tasks():
    """Delete all tasks, cancel processing tasks."""
    async with get_db() as db:
        cancel_cursor = await db.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE status = ?",
            (TaskStatus.CANCELLED.value, datetime.now().isoformat(), TaskStatus.PROCESSING.value),
        )
        delete_cursor = await db.execute(
            "DELETE FROM tasks WHERE status != ?",
            (TaskStatus.PROCESSING.value,),
        )
        await db.commit()

    return {
        "cancelled_count": cancel_cursor.rowcount,
        "deleted_count": delete_cursor.rowcount,
    }


@router.post("/delete-selected")
async def delete_selected_tasks(request: TaskIdList):
    """Delete selected tasks, cancel processing tasks."""
    if not request.task_ids:
        raise HTTPException(status_code=400, detail="No task IDs provided")

    placeholders = ",".join("?" for _ in request.task_ids)
    async with get_db() as db:
        cancel_cursor = await db.execute(
            f"UPDATE tasks SET status = ?, updated_at = ? WHERE id IN ({placeholders}) AND status = ?",
            [TaskStatus.CANCELLED.value, datetime.now().isoformat(), *request.task_ids, TaskStatus.PROCESSING.value],
        )
        delete_cursor = await db.execute(
            f"DELETE FROM tasks WHERE id IN ({placeholders}) AND status != ?",
            [*request.task_ids, TaskStatus.PROCESSING.value],
        )
        await db.commit()

    return {
        "cancelled_count": cancel_cursor.rowcount,
        "deleted_count": delete_cursor.rowcount,
    }


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    """Get a specific task by ID."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        )
        row = await cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")

        return _row_to_task(row)


@router.delete("/{task_id}")
async def delete_task(task_id: int):
    """Delete or cancel a task."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT status FROM tasks WHERE id = ?", (task_id,)
        )
        row = await cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")

        if row["status"] == TaskStatus.PROCESSING.value:
            # Mark as cancelled instead of deleting
            await db.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (TaskStatus.CANCELLED.value, task_id),
            )
        else:
            await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

        await db.commit()

    return {"status": "ok"}


@router.post("/{task_id}/retry")
async def retry_task(task_id: int):
    """Retry a failed task."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT status FROM tasks WHERE id = ?", (task_id,)
        )
        row = await cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")

        if row["status"] not in [
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
            TaskStatus.PAUSED.value,
        ]:
            raise HTTPException(
                status_code=400,
                detail="Only failed, cancelled, or paused tasks can be retried",
            )

        await db.execute(
            """
            UPDATE tasks SET status = ?, progress = 0, error_message = NULL,
            updated_at = ? WHERE id = ?
            """,
            (TaskStatus.PENDING.value, datetime.now().isoformat(), task_id),
        )
        await db.commit()

    return {"status": "ok"}


def _row_to_task(row) -> TaskResponse:
    """Convert database row to TaskResponse."""
    return TaskResponse(
        id=row["id"],
        file_path=row["file_path"],
        file_name=row["file_name"],
        status=TaskStatus(row["status"]),
        progress=row["progress"],
        source_language=row["source_language"],
        target_language=row["target_language"],
        llm_provider=row["llm_provider"],
        subtitle_track=row["subtitle_track"],
        force_override=bool(row["force_override"]) if row["force_override"] is not None else False,
        error_message=row["error_message"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        completed_at=(
            datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None
        ),
    )
