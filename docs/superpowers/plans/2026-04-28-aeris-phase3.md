# Aeris Phase 3 - 文件系统 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现文件上传下载 API、图片预览支持、文件处理工具（file_upload/file_read/file_write/file_list）。

**架构：** 本地磁盘存储 + 用户隔离路径（`uploads/{user_id}/`），文件元数据存 PostgreSQL，图片上传后生成缩略图。

**技术栈：** FastAPI UploadFile, Pillow（图片处理）, aiofiles（异步文件 IO）。

---

## 文件结构（新增）

```
aeris/
├── services/
│   └── file_service.py       # 文件存储业务逻辑
├── routers/
│   └── files.py              # 文件上传/下载/列表 API
├── tools/
│   ├── file_tools.py         # file_read, file_write, file_list 工具
│   └── __init__.py           # 导出工具
└── utils/
    └── file_utils.py         # 文件路径处理、安全检查

frontend/src/
├── components/
│   ├── FileUpload/           # 上传组件
│   │   ├── FileUpload.tsx
│   │   └── FileList.tsx
│   └── ImagePreview/         # 图片预览组件
│       └── ImagePreview.tsx
└── services/
    └── fileApi.ts            # 文件 API 调用
```

---

## 任务分解

### 任务 1：文件服务基础

**文件：**
- 创建：`aeris/utils/file_utils.py`
- 创建：`aeris/services/file_service.py`

- [ ] **步骤 1：创建 file_utils.py**

```python
import os
import re
import uuid
from pathlib import Path
from typing import Tuple

import magic

# Allowed mime types for upload
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/json",
    "application/javascript",
    "text/x-python",
    "text/x-yaml",
}

# Max file size (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

# Blocked file extensions
BLOCKED_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".sh", ".cmd",
    ".php", ".jsp", ".asp", ".aspx",
}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal.
    Remove any path components, keep only the basename.
    """
    # Get basename
    filename = os.path.basename(filename)
    # Remove null bytes
    filename = filename.replace("\x00", "")
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    return filename


def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase."""
    return os.path.splitext(filename)[1].lower()


def is_extension_blocked(filename: str) -> bool:
    """Check if file extension is blocked."""
    ext = get_file_extension(filename)
    return ext in BLOCKED_EXTENSIONS


def generate_safe_filename(original_name: str) -> Tuple[str, str]:
    """
    Generate a safe filename.
    Returns: (stored_name, extension)
    """
    ext = get_file_extension(original_name)
    # Generate UUID
    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}{ext}"
    return stored_name, ext


def get_user_upload_path(base_path: str, user_id: int) -> Path:
    """Get upload directory for a user."""
    path = Path(base_path) / str(user_id)
    return path


def get_file_path(base_path: str, user_id: int, stored_name: str) -> Path:
    """Get full file path."""
    return get_user_upload_path(base_path, user_id) / stored_name


def ensure_user_directory(base_path: str, user_id: int) -> Path:
    """Ensure user upload directory exists."""
    path = get_user_upload_path(base_path, user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def detect_mime_type(file_path: Path) -> str:
    """Detect MIME type of file."""
    try:
        return magic.from_file(str(file_path), mime=True)
    except Exception:
        return "application/octet-stream"


def is_allowed_mime_type(mime_type: str) -> bool:
    """Check if MIME type is allowed."""
    # Allow all images and common document types
    if mime_type.startswith("image/"):
        return True
    if mime_type.startswith("text/"):
        return True
    return mime_type in ALLOWED_MIME_TYPES


def format_file_size(size_bytes: int) -> str:
    """Format file size to human readable."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
```

- [ ] **步骤 2：创建 file_service.py**

```python
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from aeris.config import get_settings
from aeris.models.file_record import FileRecord
from aeris.utils.file_utils import (
    sanitize_filename,
    generate_safe_filename,
    ensure_user_directory,
    get_file_path,
    detect_mime_type,
    is_allowed_mime_type,
    is_extension_blocked,
    format_file_size,
    MAX_FILE_SIZE,
)

settings = get_settings()


class FileService:
    """File storage and management service."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.base_path = Path(settings.uploads_dir)

    async def save_file(
        self,
        user_id: int,
        original_name: str,
        content_type: str,
        file_data: bytes,
        conversation_id: Optional[int] = None,
    ) -> FileRecord:
        """
        Save uploaded file to disk and database.

        1. Validate file
        2. Generate safe filename
        3. Save to disk
        4. Create database record
        5. Generate thumbnail for images
        """
        # Validate
        if len(file_data) > MAX_FILE_SIZE:
            raise ValueError(f"File too large. Max size: {MAX_FILE_SIZE}")

        original_name = sanitize_filename(original_name)

        if is_extension_blocked(original_name):
            raise ValueError(f"File type not allowed: {original_name}")

        # Generate safe filename
        stored_name, _ = generate_safe_filename(original_name)

        # Ensure directory exists
        user_dir = ensure_user_directory(self.base_path, user_id)
        file_path = user_dir / stored_name

        # Save to disk
        with open(file_path, "wb") as f:
            f.write(file_data)

        # Detect MIME type
        mime_type = detect_mime_type(file_path)

        if not is_allowed_mime_type(mime_type):
            # Delete file and raise error
            file_path.unlink()
            raise ValueError(f"File type not allowed: {mime_type}")

        # Generate thumbnail for images
        if mime_type.startswith("image/"):
            await self._generate_thumbnail(user_id, stored_name)

        # Create database record
        relative_path = f"uploads/{user_id}/{stored_name}"
        file_record = FileRecord(
            user_id=user_id,
            conversation_id=conversation_id,
            original_name=original_name,
            stored_name=stored_name,
            mime_type=mime_type,
            size_bytes=len(file_data),
            storage_path=relative_path,
            status="ready",
        )

        self.session.add(file_record)
        await self.session.commit()
        await self.session.refresh(file_record)

        return file_record

    async def _generate_thumbnail(self, user_id: int, stored_name: str, size: int = 200):
        """Generate thumbnail for image."""
        try:
            user_dir = ensure_user_directory(self.base_path, user_id)
            file_path = user_dir / stored_name
            thumb_path = user_dir / f"thumb_{stored_name}"

            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Calculate new size maintaining aspect ratio
                width, height = img.size
                if width > height:
                    new_width = size
                    new_height = int(height * (size / width))
                else:
                    new_height = size
                    new_width = int(width * (size / height))

                img.thumbnail((new_width, new_height), Image.LANCZOS)
                img.save(thumb_path, "JPEG", quality=85)
        except Exception:
            # Thumbnail generation is optional
            pass

    async def get_file(self, user_id: int, file_id: int) -> Optional[FileRecord]:
        """Get file record by ID."""
        result = await self.session.execute(
            select(FileRecord)
            .where(FileRecord.id == file_id)
            .where(FileRecord.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_file_path(self, file_record: FileRecord) -> Path:
        """Get absolute file path from record."""
        return self.base_path / str(file_record.user_id) / file_record.stored_name

    async def get_thumbnail_path(self, file_record: FileRecord) -> Optional[Path]:
        """Get thumbnail path if exists."""
        if not file_record.mime_type.startswith("image/"):
            return None

        thumb_path = (
            self.base_path
            / str(file_record.user_id)
            / f"thumb_{file_record.stored_name}"
        )
        if thumb_path.exists():
            return thumb_path
        return None

    async def list_files(
        self,
        user_id: int,
        conversation_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[FileRecord]:
        """List user's files."""
        query = select(FileRecord).where(FileRecord.user_id == user_id)

        if conversation_id:
            query = query.where(FileRecord.conversation_id == conversation_id)

        query = query.order_by(FileRecord.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete_file(self, user_id: int, file_id: int) -> bool:
        """Delete file from disk and database."""
        file_record = await self.get_file(user_id, file_id)
        if not file_record:
            return False

        # Delete from disk
        file_path = await self.get_file_path(file_record)
        if file_path.exists():
            file_path.unlink()

        # Delete thumbnail if exists
        thumb_path = await self.get_thumbnail_path(file_record)
        if thumb_path and thumb_path.exists():
            thumb_path.unlink()

        # Delete from database
        await self.session.delete(file_record)
        await self.session.commit()

        return True

    async def read_file_content(self, file_record: FileRecord) -> str:
        """
        Read file content as text.
        For images, return base64 data URL.
        For other files, try to read as text.
        """
        file_path = await self.get_file_path(file_record)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_record.original_name}")

        # Images: return base64
        if file_record.mime_type.startswith("image/"):
            import base64
            with open(file_path, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode()
            return f"data:{file_record.mime_type};base64,{b64}"

        # Text files: read as text
        if file_record.mime_type.startswith("text/") or file_record.mime_type in [
            "application/json",
            "application/javascript",
        ]:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                raise ValueError(f"Cannot read file as text: {file_record.original_name}")

        # PDF: extract text (optional for MVP)
        if file_record.mime_type == "application/pdf":
            try:
                import PyPDF2
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            except Exception as e:
                raise ValueError(f"Failed to extract PDF text: {e}")

        raise ValueError(f"Cannot read file content: {file_record.mime_type}")

    async def write_file(
        self,
        user_id: int,
        filename: str,
        content: str,
        conversation_id: Optional[int] = None,
    ) -> FileRecord:
        """
        Write content to file (for agent to generate files).
        """
        # Determine mime type from extension
        ext = Path(filename).suffix.lower()
        mime_type_map = {
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".json": "application/json",
            ".js": "application/javascript",
            ".py": "text/x-python",
            ".yaml": "text/x-yaml",
            ".yml": "text/x-yaml",
        }
        mime_type = mime_type_map.get(ext, "text/plain")

        # Encode content
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content

        # Save using existing method
        return await self.save_file(
            user_id=user_id,
            original_name=filename,
            content_type=mime_type,
            file_data=content_bytes,
            conversation_id=conversation_id,
        )
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/utils/file_utils.py aeris/services/file_service.py
git commit -m "feat: add file service with upload/download/thumbnail support"
```

---

### 任务 2：文件 API 路由

**文件：**
- 创建：`aeris/routers/files.py`
- 修改：`aeris/main.py`（添加文件路由）

- [ ] **步骤 1：创建 files.py**

```python
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from aeris.database import get_session
from aeris.routers.auth import get_current_user, TokenData
from aeris.services.file_service import FileService
from aeris.schemas.files import FileUploadResponse, FileListResponse

router = APIRouter(prefix="/files", tags=["files"])


async def get_file_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FileService:
    return FileService(session)


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: Annotated[UploadFile, File(...)],
    conversation_id: Annotated[Optional[int], Form(None)] = None,
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    file_service: Annotated[FileService, Depends(get_file_service)] = None,
):
    """Upload a file."""
    try:
        content = await file.read()
        file_record = await file_service.save_file(
            user_id=current_user.user_id,
            original_name=file.filename,
            content_type=file.content_type or "application/octet-stream",
            file_data=content,
            conversation_id=conversation_id,
        )

        return FileUploadResponse(
            id=file_record.id,
            original_name=file_record.original_name,
            mime_type=file_record.mime_type,
            size_bytes=file_record.size_bytes,
            size_display=file_service.format_file_size(file_record.size_bytes),
            created_at=file_record.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("", response_model=List[FileListResponse])
async def list_files(
    conversation_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    file_service: Annotated[FileService, Depends(get_file_service)] = None,
):
    """List user's files."""
    files = await file_service.list_files(
        user_id=current_user.user_id,
        conversation_id=conversation_id,
        skip=skip,
        limit=limit,
    )

    return [
        FileListResponse(
            id=f.id,
            original_name=f.original_name,
            mime_type=f.mime_type,
            size_bytes=f.size_bytes,
            size_display=FileService.format_file_size(f.size_bytes),
            is_image=f.mime_type.startswith("image/"),
            created_at=f.created_at,
        )
        for f in files
    ]


@router.get("/{file_id}")
async def download_file(
    file_id: int,
    thumbnail: bool = False,
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    file_service: Annotated[FileService, Depends(get_file_service)] = None,
):
    """Download a file."""
    file_record = await file_service.get_file(current_user.user_id, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    if thumbnail and file_record.mime_type.startswith("image/"):
        thumb_path = await file_service.get_thumbnail_path(file_record)
        if thumb_path:
            return FileResponse(
                path=str(thumb_path),
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=86400"},
            )

    file_path = await file_service.get_file_path(file_record)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=str(file_path),
        filename=file_record.original_name,
        media_type=file_record.mime_type,
        headers={"Cache-Control": "private"},
    )


@router.get("/{file_id}/content")
async def get_file_content(
    file_id: int,
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    file_service: Annotated[FileService, Depends(get_file_service)] = None,
):
    """Get file content as text or base64."""
    file_record = await file_service.get_file(current_user.user_id, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = await file_service.read_file_content(file_record)
        return {"content": content, "mime_type": file_record.mime_type}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on disk")


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: int,
    current_user: Annotated[TokenData, Depends(get_current_user)] = None,
    file_service: Annotated[FileService, Depends(get_file_service)] = None,
):
    """Delete a file."""
    success = await file_service.delete_file(current_user.user_id, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return None
```

- [ ] **步骤 2：创建 schemas/files.py**

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    id: int
    original_name: str
    mime_type: str
    size_bytes: int
    size_display: str
    created_at: datetime


class FileListResponse(BaseModel):
    id: int
    original_name: str
    mime_type: str
    size_bytes: int
    size_display: str
    is_image: bool
    created_at: datetime
```

- [ ] **步骤 3：修改 main.py 添加文件路由**

在 `main.py` 中添加：

```python
from aeris.routers import files
app.include_router(files.router, prefix="/api/v1")
```

- [ ] **步骤 4：Commit**

```bash
git add aeris/routers/files.py aeris/schemas/files.py aeris/main.py
git commit -m "feat: add file upload/download/list API routes"
```

---

### 任务 3：文件处理工具

**文件：**
- 创建：`aeris/tools/file_tools.py`
- 修改：`aeris/main.py`（注册文件工具）

- [ ] **步骤 1：创建 file_tools.py**

```python
import base64
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from aeris.database import get_session_context
from aeris.models.file_record import FileRecord
from aeris.services.file_service import FileService
from aeris.tools.base import Tool, ToolParameter, ToolResult


class FileUploadTool(Tool):
    """Upload a file to the system."""

    name = "file_upload"
    description = "Upload a file with base64 encoded content. Returns file metadata."
    parameters = [
        ToolParameter(
            name="filename",
            type="string",
            description="Original filename",
            required=True,
        ),
        ToolParameter(
            name="content_base64",
            type="string",
            description="Base64 encoded file content",
            required=True,
        ),
        ToolParameter(
            name="mime_type",
            type="string",
            description="MIME type of the file (optional, auto-detected if not provided)",
            required=False,
        ),
    ]

    async def execute(
        self,
        filename: str,
        content_base64: str,
        mime_type: Optional[str] = None,
        _context: Dict = None,
    ) -> ToolResult:
        try:
            user_id = _context.get("user_id") if _context else None
            conversation_id = _context.get("conversation_id") if _context else None

            if not user_id:
                return ToolResult(success=False, error="User context not available")

            # Decode base64
            try:
                content = base64.b64decode(content_base64)
            except Exception:
                return ToolResult(success=False, error="Invalid base64 content")

            # Use file service
            async with get_session_context() as session:
                file_service = FileService(session)
                file_record = await file_service.save_file(
                    user_id=user_id,
                    original_name=filename,
                    content_type=mime_type or "application/octet-stream",
                    file_data=content,
                    conversation_id=conversation_id,
                )

            return ToolResult(
                success=True,
                data={
                    "file_id": file_record.id,
                    "filename": file_record.original_name,
                    "mime_type": file_record.mime_type,
                    "size_bytes": file_record.size_bytes,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FileReadTool(Tool):
    """Read content of an uploaded file."""

    name = "file_read"
    description = "Read the content of a previously uploaded file. Returns text content for text/PDF files, or base64 for images."
    parameters = [
        ToolParameter(
            name="file_id",
            type="integer",
            description="ID of the file to read",
            required=True,
        ),
    ]

    async def execute(
        self,
        file_id: int,
        _context: Dict = None,
    ) -> ToolResult:
        try:
            user_id = _context.get("user_id") if _context else None

            if not user_id:
                return ToolResult(success=False, error="User context not available")

            async with get_session_context() as session:
                file_service = FileService(session)
                file_record = await file_service.get_file(user_id, file_id)

                if not file_record:
                    return ToolResult(success=False, error=f"File {file_id} not found")

                content = await file_service.read_file_content(file_record)

            return ToolResult(
                success=True,
                data={
                    "file_id": file_id,
                    "filename": file_record.original_name,
                    "mime_type": file_record.mime_type,
                    "content": content,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FileWriteTool(Tool):
    """Write content to a file (create new file)."""

    name = "file_write"
    description = "Create a new file with the given content. Useful for generating reports, code, or any text output."
    parameters = [
        ToolParameter(
            name="filename",
            type="string",
            description="Name of the file to create (e.g., 'report.md', 'code.py')",
            required=True,
        ),
        ToolParameter(
            name="content",
            type="string",
            description="Content to write to the file",
            required=True,
        ),
    ]

    async def execute(
        self,
        filename: str,
        content: str,
        _context: Dict = None,
    ) -> ToolResult:
        try:
            user_id = _context.get("user_id") if _context else None
            conversation_id = _context.get("conversation_id") if _context else None

            if not user_id:
                return ToolResult(success=False, error="User context not available")

            async with get_session_context() as session:
                file_service = FileService(session)
                file_record = await file_service.write_file(
                    user_id=user_id,
                    filename=filename,
                    content=content,
                    conversation_id=conversation_id,
                )

            return ToolResult(
                success=True,
                data={
                    "file_id": file_record.id,
                    "filename": file_record.original_name,
                    "mime_type": file_record.mime_type,
                    "size_bytes": file_record.size_bytes,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FileListTool(Tool):
    """List uploaded files."""

    name = "file_list"
    description = "List uploaded files for the current user, optionally filtered by conversation."
    parameters = [
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of files to return (default 20)",
            required=False,
        ),
    ]

    async def execute(
        self,
        limit: int = 20,
        _context: Dict = None,
    ) -> ToolResult:
        try:
            user_id = _context.get("user_id") if _context else None
            conversation_id = _context.get("conversation_id") if _context else None

            if not user_id:
                return ToolResult(success=False, error="User context not available")

            async with get_session_context() as session:
                file_service = FileService(session)
                files = await file_service.list_files(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    limit=limit,
                )

            return ToolResult(
                success=True,
                data={
                    "files": [
                        {
                            "id": f.id,
                            "filename": f.original_name,
                            "mime_type": f.mime_type,
                            "size_bytes": f.size_bytes,
                            "created_at": f.created_at.isoformat(),
                        }
                        for f in files
                    ],
                    "count": len(files),
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


def register_file_tools(registry):
    """Register all file tools."""
    registry.register(FileUploadTool())
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(FileListTool())
```

- [ ] **步骤 2：修改 main.py 注册文件工具**

在 `lifespan` 函数中：

```python
# Register tools
from aeris.tools.base import get_tool_registry
from aeris.tools.conversation_search import register_conversation_search_tool
from aeris.tools.file_tools import register_file_tools

registry = get_tool_registry()
register_conversation_search_tool(registry)
register_file_tools(registry)
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/tools/file_tools.py aeris/main.py
git commit -m "feat: add file tools (upload, read, write, list)"
```

---

### 任务 4：测试文件服务

**文件：**
- 创建：`tests/test_file_service.py`

- [ ] **步骤 1：创建 test_file_service.py**

```python
import pytest
from unittest.mock import Mock, patch
import io


@pytest.mark.asyncio
async def test_upload_file(client, db_session):
    """Test file upload."""
    from aeris.services.auth_service import AuthService
    from aeris.utils.security import create_access_token

    # Create user
    auth_service = AuthService(db_session)
    user = await auth_service.create_user("fileuser", "password123")
    token = auth_service.create_access_token_for_user(user)

    # Upload file
    file_content = b"Test file content"
    response = await client.post(
        "/api/v1/files/upload",
        files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["original_name"] == "test.txt"
    assert data["mime_type"] == "text/plain"
    assert data["size_bytes"] == len(file_content)


@pytest.mark.asyncio
async def test_list_files(client, db_session):
    """Test list files."""
    from aeris.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    user = await auth_service.create_user("fileuser2", "password123")
    token = auth_service.create_access_token_for_user(user)

    # List files (empty)
    response = await client.get(
        "/api/v1/files",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **步骤 2：Commit**

```bash
git add tests/test_file_service.py
git commit -m "test: add file service tests"
```

---

## 自检

### 规格覆盖度检查

| 规格需求 | 实现任务 |
|---------|---------|
| 文件上传 API | ✅ 任务 1, 2 |
| 文件下载 API | ✅ 任务 2 |
| 图片缩略图 | ✅ 任务 1 |
| 文件隔离（按用户） | ✅ 任务 1 |
| file_upload 工具 | ✅ 任务 3 |
| file_read 工具 | ✅ 任务 3 |
| file_write 工具 | ✅ 任务 3 |
| file_list 工具 | ✅ 任务 3 |
| 测试覆盖 | ✅ 任务 4 |

### 文件职责

- `file_utils.py`: 文件路径处理、安全检查、MIME 检测
- `file_service.py`: 文件存储业务逻辑
- `files.py`: HTTP API 路由
- `file_tools.py`: Agent 可调用的工具
- `files.py` (schemas): Pydantic schemas

---

## 执行方式

**计划已完成并保存到 `docs/superpowers/plans/2026-04-28-aeris-phase3.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理

**2. 内联执行** - 在当前会话中使用 executing-plans 技能

**选哪种方式？**
