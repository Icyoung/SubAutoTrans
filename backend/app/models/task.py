from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskCreate(BaseModel):
    file_path: str
    target_language: str = "Chinese"
    llm_provider: str = "openai"
    subtitle_track: Optional[int] = None


class TaskResponse(BaseModel):
    id: int
    file_path: str
    file_name: str
    status: TaskStatus
    progress: int
    source_language: Optional[str]
    target_language: str
    llm_provider: str
    subtitle_track: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    progress: Optional[int] = None
    error_message: Optional[str] = None


class DirectoryTaskCreate(BaseModel):
    directory_path: str
    target_language: str = "Chinese"
    llm_provider: str = "openai"
    recursive: bool = False


class WatcherCreate(BaseModel):
    path: str
    target_language: str = "Chinese"
    llm_provider: str = "openai"


class ScanStats(BaseModel):
    scanned: int
    triggered: int


class WatcherResponse(BaseModel):
    id: int
    path: str
    enabled: bool
    target_language: str
    llm_provider: str
    created_at: datetime
    scan_stats: Optional[ScanStats] = None


class TaskIdList(BaseModel):
    task_ids: list[int]


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
    limit: int
    offset: int
