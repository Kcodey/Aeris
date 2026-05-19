from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from meditatio.database import get_session_context
from meditatio.models.file_record import FileRecord
from meditatio.services.file_service import FileService
from meditatio.tools.base import Tool, ToolParameter, ToolResult


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
    """Register file tools."""
    registry.register(FileWriteTool())
    registry.register(FileListTool())
