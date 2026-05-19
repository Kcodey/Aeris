import pytest
from unittest.mock import Mock, patch
import io


@pytest.mark.asyncio
async def test_upload_file(client, db_session):
    """Test file upload."""
    from meditatio.services.auth_service import AuthService
    from meditatio.utils.security import create_access_token

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
    from meditatio.services.auth_service import AuthService

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
