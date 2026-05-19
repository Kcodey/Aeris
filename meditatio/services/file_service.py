"""File storage and management service."""

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

        # Excel: extract as markdown table
        if file_record.mime_type in [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
            "application/vnd.ms-excel",  # .xls
        ]:
            try:
                import pandas as pd
                # Read all sheets
                xls = pd.ExcelFile(file_path)
                result = []
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    # Convert to markdown table (first 100 rows for preview)
                    preview_df = df.head(100)
                    md_table = preview_df.to_markdown(index=False)
                    result.append(f"## Sheet: {sheet_name}\n\n{md_table}")
                    if len(df) > 100:
                        result.append(f"\n*... ({len(df) - 100} more rows) ...*")
                return "\n\n".join(result)
            except Exception as e:
                raise ValueError(f"Failed to extract Excel content: {e}")

        # Word: extract text
        if file_record.mime_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
            "application/msword",  # .doc
        ]:
            try:
                import docx
                doc = docx.Document(file_path)
                paragraphs = []
                for para in doc.paragraphs:
                    if para.text.strip():
                        paragraphs.append(para.text)
                text = "\n".join(paragraphs)
                # Truncate if too long
                if len(text) > 8000:
                    text = text[:8000] + "\n... (内容已截断)"
                return text
            except Exception as e:
                raise ValueError(f"Failed to extract Word content: {e}")

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
