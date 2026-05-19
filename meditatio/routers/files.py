from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from aeris.database import get_session
from aeris.routers.auth import get_current_user, TokenData
from aeris.services.file_service import FileService
from aeris.schemas.files import FileUploadResponse, FileListResponse
from aeris.utils.file_utils import format_file_size

router = APIRouter(prefix="/files", tags=["files"])


async def get_file_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FileService:
    return FileService(session)


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: Annotated[UploadFile, File(...)],
    conversation_id: Annotated[Optional[int], Form()] = None,
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
            size_display=format_file_size(file_record.size_bytes),
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
            size_display=format_file_size(f.size_bytes),
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
