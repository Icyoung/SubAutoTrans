import aiosqlite
import os
from contextlib import asynccontextmanager

DATABASE_PATH = "./data/tasks.db"


async def init_db():
    """Initialize database tables."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                source_language TEXT,
                target_language TEXT NOT NULL,
                llm_provider TEXT NOT NULL,
                subtitle_track INTEGER,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS watchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                enabled INTEGER DEFAULT 1,
                target_language TEXT NOT NULL,
                llm_provider TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Track translated files to avoid re-translation
        await db.execute("""
            CREATE TABLE IF NOT EXISTS translated_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                target_language TEXT NOT NULL,
                output_path TEXT,
                translated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_path, target_language)
            )
        """)

        # Add indexes for faster lookups
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_file_language
            ON tasks(file_path, target_language)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_translated_files_lookup
            ON translated_files(file_path, target_language)
        """)

        await db.commit()


@asynccontextmanager
async def get_db():
    """Get database connection."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()
