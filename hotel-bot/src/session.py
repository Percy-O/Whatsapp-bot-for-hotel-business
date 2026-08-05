"""
Session Manager — Conversation State

Manages guest conversation state using in-memory store with Spaxce API backup.
Handles session creation, retrieval, expiration, and history management.
"""

from datetime import datetime, timedelta
import json
import logging
from src.spaxce_api_client import get_bot_session, save_bot_session

logger = logging.getLogger(__name__)

# In-memory session store (cache)
_sessions = {}


async def get_session(phone: str) -> dict:
    """
    Retrieve or create a session for a phone number.
    
    Checks in-memory store first, then Spaxce API, then creates fresh session.
    
    Args:
        phone: Guest's phone number
    
    Returns:
        Session dict with phone, flow, step, data, history, last_active
    """
    # Check in-memory
    if phone in _sessions:
        return _sessions[phone]
    
    # Check Spaxce API
    try:
        session = await get_bot_session(phone)
        if session:
            _sessions[phone] = session
            return session
    except Exception as e:
        logger.error(f"Error loading session from Spaxce API: {e}")
    
    # Create fresh session
    session = {
        "phone": phone,
        "flow": None,
        "step": None,
        "data": {},
        "history": [],
        "last_active": datetime.now().isoformat()
    }
    _sessions[phone] = session
    return session


async def save_session(phone: str, session: dict) -> None:
    """
    Save session to in-memory store and Spaxce API.
    """
    session["last_active"] = datetime.now().isoformat()
    _sessions[phone] = session
    
    try:
        await save_bot_session(phone, session)
    except Exception as e:
        logger.error(f"Error saving session to Spaxce API: {e}")


async def clear_session(phone: str) -> None:
    """
    Clear session from memory and Spaxce API.
    """
    if phone in _sessions:
        del _sessions[phone]
    
    try:
        # We can clear it by saving an empty state or we could add a DELETE endpoint
        # For now, let's just save an empty dict or rely on session expiration
        await save_bot_session(phone, {})
    except Exception as e:
        logger.error(f"Error clearing session: {e}")


def is_session_expired(session: dict) -> bool:
    """
    Check if session has expired (30 minutes of inactivity).
    """
    if not session.get("last_active"):
        return True
    
    try:
        last_active = datetime.fromisoformat(session["last_active"])
        elapsed = datetime.now() - last_active
        return elapsed > timedelta(minutes=30)
    except Exception:
        return True


def append_history(session: dict, role: str, content: str) -> dict:
    """
    Append message to session history (keep last 10 messages).
    """
    if "history" not in session:
        session["history"] = []
        
    session["history"].append({
        "role": role,
        "content": content
    })
    
    # Keep only last 10 messages
    if len(session["history"]) > 10:
        session["history"] = session["history"][-10:]
    
    return session
