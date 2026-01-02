import asyncio
import os
from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging
from ..database import get_db
from ..models.task import WatcherCreate, WatcherResponse
from ..services.watcher import directory_watcher

router = APIRouter(prefix="/api/watchers", tags=["watchers"])

logger = logging.getLogger(__name__)



def _schedule_scan(path: str, target_language: str, llm_provider: str):
    async def _run():
        try:
            await directory_watcher.scan_directory(path, target_language, llm_provider)
        except Exception as e:
            logger.error(f"Watcher scan failed for {path}: {e}")

    asyncio.create_task(_run())

@router.get("", response_model=list[WatcherResponse])
async def list_watchers():
    """List all directory watchers."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM watchers ORDER BY created_at DESC")
        rows = await cursor.fetchall()

        return [
            WatcherResponse(
                id=row["id"],
                path=row["path"],
                enabled=bool(row["enabled"]),
                target_language=row["target_language"],
                llm_provider=row["llm_provider"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]


@router.post("", response_model=WatcherResponse)
async def create_watcher(watcher: WatcherCreate):
    """Create a new directory watcher."""
    if not os.path.isdir(watcher.path):
        raise HTTPException(status_code=404, detail="Directory not found")

    async with get_db() as db:
        # Check if already watching
        cursor = await db.execute(
            "SELECT id FROM watchers WHERE path = ?", (watcher.path,)
        )
        if await cursor.fetchone():
            raise HTTPException(
                status_code=400, detail="Directory is already being watched"
            )

        cursor = await db.execute(
            """
            INSERT INTO watchers (path, target_language, llm_provider)
            VALUES (?, ?, ?)
            """,
            (watcher.path, watcher.target_language, watcher.llm_provider),
        )
        await db.commit()

        watcher_id = cursor.lastrowid

        # Start watching
        try:
            directory_watcher.start_watching(
                watcher_id,
                watcher.path,
                watcher.target_language,
                watcher.llm_provider,
            )

            # Scan existing files in the directory (async)
            _schedule_scan(
                watcher.path,
                watcher.target_language,
                watcher.llm_provider,
            )
        except Exception as e:
            # Rollback if watching fails
            await db.execute("DELETE FROM watchers WHERE id = ?", (watcher_id,))
            await db.commit()
            raise HTTPException(status_code=500, detail=str(e))

        cursor = await db.execute(
            "SELECT * FROM watchers WHERE id = ?", (watcher_id,)
        )
        row = await cursor.fetchone()

        return WatcherResponse(
            id=row["id"],
            path=row["path"],
            enabled=bool(row["enabled"]),
            target_language=row["target_language"],
            llm_provider=row["llm_provider"],
            created_at=datetime.fromisoformat(row["created_at"]),
            scan_stats=None,
        )


@router.delete("/{watcher_id}")
async def delete_watcher(watcher_id: int):
    """Delete a directory watcher."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM watchers WHERE id = ?", (watcher_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Watcher not found")

        # Stop watching
        directory_watcher.stop_watching(watcher_id)

        await db.execute("DELETE FROM watchers WHERE id = ?", (watcher_id,))
        await db.commit()

    return {"status": "ok"}


@router.post("/{watcher_id}/toggle")
async def toggle_watcher(watcher_id: int):
    """Enable or disable a watcher."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM watchers WHERE id = ?", (watcher_id,)
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Watcher not found")

        new_enabled = not bool(row["enabled"])

        await db.execute(
            "UPDATE watchers SET enabled = ? WHERE id = ?",
            (1 if new_enabled else 0, watcher_id),
        )
        await db.commit()

        scan_stats = None
        if new_enabled:
            directory_watcher.start_watching(
                watcher_id,
                row["path"],
                row["target_language"],
                row["llm_provider"],
            )
            # Scan existing files when enabling (async)
            _schedule_scan(
                row["path"],
                row["target_language"],
                row["llm_provider"],
            )
        else:
            directory_watcher.stop_watching(watcher_id)

    return {"enabled": new_enabled, "scan_stats": None}
