import os
import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/files", tags=["files"])


class FileInfo(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None


class BrowseResponse(BaseModel):
    current_path: str
    parent_path: Optional[str]
    items: list[FileInfo]


@router.get("/browse", response_model=BrowseResponse)
async def browse_files(
    path: str = Query(default="~", description="Directory path to browse"),
):
    """Browse server file system."""
    # Expand user home directory
    if path.startswith("~"):
        path = os.path.expanduser(path)

    path = os.path.abspath(path)

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path not found")

    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Path is not a directory")

    items = []

    try:
        for name in sorted(os.listdir(path)):
            full_path = os.path.join(path, name)

            # Skip hidden files
            if name.startswith("."):
                continue

            try:
                is_dir = os.path.isdir(full_path)
                size = None if is_dir else os.path.getsize(full_path)

                # Only show directories and supported subtitle files
                if is_dir or name.lower().endswith((".mkv", ".srt", ".ass")):
                    items.append(
                        FileInfo(
                            name=name,
                            path=full_path,
                            is_dir=is_dir,
                            size=size,
                        )
                    )
            except (PermissionError, OSError):
                continue

    except PermissionError:
        raise HTTPException(
            status_code=403, detail="Permission denied to read directory"
        )

    # Sort: directories first, then files
    items.sort(key=lambda x: (not x.is_dir, x.name.lower()))

    parent_path = os.path.dirname(path) if path != "/" else None

    return BrowseResponse(
        current_path=path,
        parent_path=parent_path,
        items=items,
    )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    destination: str = Query(default="./data/uploads"),
):
    """Upload an MKV file to the server."""
    if not file.filename.lower().endswith((".mkv", ".srt", ".ass")):
        raise HTTPException(
            status_code=400, detail="Only MKV, SRT, or ASS files are allowed"
        )

    # Ensure destination directory exists
    os.makedirs(destination, exist_ok=True)

    file_path = os.path.join(destination, file.filename)

    # Avoid overwriting existing files
    if os.path.exists(file_path):
        base, ext = os.path.splitext(file.filename)
        counter = 1
        while os.path.exists(file_path):
            file_path = os.path.join(destination, f"{base}_{counter}{ext}")
            counter += 1

    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            await f.write(chunk)

    return {
        "filename": os.path.basename(file_path),
        "path": file_path,
        "size": os.path.getsize(file_path),
    }


@router.get("/subtitle-tracks")
async def get_subtitle_tracks(file_path: str):
    """Get subtitle tracks from an MKV file."""
    from ..services.subtitle import get_subtitle_tracks

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        info = await get_subtitle_tracks(file_path)
        return {
            "file_path": info.file_path,
            "tracks": [
                {
                    "index": t.index,
                    "codec": t.codec,
                    "language": t.language,
                    "title": t.title,
                }
                for t in info.tracks
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
