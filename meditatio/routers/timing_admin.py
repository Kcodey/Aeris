"""Admin API for timing trace management."""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from meditatio.utils.timing_collector import get_collector
from meditatio.routers.auth import get_current_user

router = APIRouter(prefix="/admin/timing", tags=["admin", "timing"])


@router.get("/status")
async def get_timing_status(current_user: dict = Depends(get_current_user)):
    """Get timing collector status."""
    # TODO: Add admin check
    collector = get_collector()
    return collector.get_status()


@router.post("/enable/conversation/{conversation_id}")
async def enable_for_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Enable timing trace for a specific conversation."""
    collector = get_collector()
    collector.enable_for_conversation(conversation_id)
    return {
        "status": "ok",
        "conversation_id": conversation_id,
        "action": "enabled"
    }


@router.post("/disable/conversation/{conversation_id}")
async def disable_for_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Disable timing trace for a specific conversation."""
    collector = get_collector()
    collector.disable_for_conversation(conversation_id)
    return {
        "status": "ok",
        "conversation_id": conversation_id,
        "action": "disabled"
    }


@router.post("/enable/user/{user_id}")
async def enable_for_user(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Enable timing trace for a specific user."""
    collector = get_collector()
    collector.enable_for_user(user_id)
    return {
        "status": "ok",
        "user_id": user_id,
        "action": "enabled"
    }


@router.post("/disable/user/{user_id}")
async def disable_for_user(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Disable timing trace for a specific user."""
    collector = get_collector()
    collector.disable_for_user(user_id)
    return {
        "status": "ok",
        "user_id": user_id,
        "action": "disabled"
    }


@router.post("/configure")
async def configure_timing(config: Dict[str, Any], current_user: dict = Depends(get_current_user)):
    """Configure timing collector settings."""
    collector = get_collector()
    collector.configure(config)
    return {
        "status": "ok",
        "config": config
    }
