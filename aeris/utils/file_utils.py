"""File utilities for path handling, security checks, and MIME detection."""

import mimetypes
import os
import re
import uuid
from pathlib import Path
from typing import Tuple

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
    """Detect MIME type of file using standard library."""
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or "application/octet-stream"


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


def get_thumbnail_path(base_path: str, user_id: int, stored_name: str) -> Path:
    """Get thumbnail path for image."""
    user_dir = get_user_upload_path(base_path, user_id)
    return user_dir / f"thumb_{stored_name}"
