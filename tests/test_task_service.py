import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch


@pytest.fixture
def mock_scheduler():
    """Mock task scheduler for tests."""
    mock = Mock()
    mock_job = Mock()
    mock_job.next_run_time = datetime.utcnow() + timedelta(days=1)
    mock.scheduler = Mock()
    mock.scheduler.get_job.return_value = mock_job
    return mock


@pytest.mark.asyncio
async def test_create_cron_task(client, db_session, mock_scheduler):
    """Test creating a cron task."""
    from meditatio.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    user = await auth_service.create_user("taskuser", "password123")
    token = auth_service.create_access_token_for_user(user)

    with patch("meditatio.services.task_service.get_task_scheduler", return_value=mock_scheduler):
        response = await client.post(
            "/api/v1/tasks",
            json={
                "name": "Daily Summary",
                "description": "Send daily summary at 9am",
                "trigger_type": "cron",
                "trigger_config": {"cron": "0 9 * * *"},
                "task_payload": {
                    "type": "chat_completion",
                    "message": "Give me a summary of today's activities",
                },
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Daily Summary"
    assert data["trigger_type"] == "cron"
    assert data["trigger_config"]["cron"] == "0 9 * * *"


@pytest.mark.asyncio
async def test_list_tasks(client, db_session):
    """Test listing tasks."""
    from meditatio.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    user = await auth_service.create_user("taskuser2", "password123")
    token = auth_service.create_access_token_for_user(user)

    response = await client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []
