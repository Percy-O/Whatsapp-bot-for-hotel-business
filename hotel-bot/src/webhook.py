"""
Webhook Receiver — Meta WhatsApp Cloud API Integration

Receives incoming WhatsApp messages from Meta's Cloud API,
validates webhook requests, and parses message payloads.

Configuration is automatically synced from Spaxce REST API.
"""

from fastapi.responses import PlainTextResponse, JSONResponse
import os
import logging
from src.spaxce_api_client import get_verify_token, is_bot_enabled

logger = logging.getLogger(__name__)


async def verify_webhook(mode: str, challenge: str, verify_token: str):
    """
    Verify webhook endpoint with Meta Cloud API (2025 standard).
    
    Args:
        mode: Hub subscription mode (should be "subscribe")
        challenge: Challenge string from Meta
        verify_token: Token from Spaxce API (for validation)
    
    Returns:
        PlainTextResponse with challenge if valid, 403 if invalid
    """
    # Get expected token from Spaxce API
    expected_token = await get_verify_token()
    
    logger.info(f"Webhook verification attempt: mode={mode}, token_match={verify_token == expected_token}")
    
    if mode == "subscribe" and verify_token == expected_token:
        logger.info("✓ Webhook verified successfully")
        return PlainTextResponse(challenge, status_code=200)
    else:
        logger.warning(f"✗ Webhook verification failed: expected_token={expected_token}, got={verify_token}")
        return JSONResponse(
            {"error": "Invalid verification token"},
            status_code=403
        )


def parse_incoming(body: dict) -> dict | None:
    """
    Parse incoming message from Meta webhook payload.
    
    Args:
        body: Full webhook payload from Meta
    
    Returns:
        Dict with: phone, message, message_id, timestamp
        None if not a text message
    """
    try:
        # Check if this is actually a message event
        object_type = body.get("object")
        if object_type != "whatsapp_business_account":
            logger.info(f"ℹ️ Webhook object type: {object_type} (expected whatsapp_business_account)")
            return None
        
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        
        # Check what type of change this is
        change_type = changes.get("field")
        logger.info(f"ℹ️ Change type: {change_type}")
        
        messages = value.get("messages", [])
        
        if not messages:
            logger.info("ℹ️ No messages in webhook (might be status update)")
            return None
        
        message = messages[0]
        
        # Only handle text messages for now
        msg_type = message.get("type")
        if msg_type != "text":
            logger.info(f"ℹ️ Non-text message received: {msg_type}")
            return None
        
        phone = message.get("from")
        text_body = message.get("text", {}).get("body", "")
        msg_id = message.get("id")
        
        logger.info(f"✓ Valid message: phone={phone}, text='{text_body}', id={msg_id}")
        
        return {
            "phone": phone,
            "message": text_body,
            "message_id": msg_id,
            "timestamp": message.get("timestamp")
        }
    except (KeyError, IndexError, AttributeError) as e:
        logger.warning(f"⚠️ Error parsing message structure: {e}")
        logger.debug(f"Full body: {body}")
        return None


async def handle_incoming(body: dict) -> None:
    """
    Handle incoming message from Meta webhook.
    
    Extract message data, log it, and route to appropriate handler.
    
    Args:
        body: Full webhook payload from Meta
    """
    try:
        logger.info(f"📥 Webhook received")
        logger.debug(f"Payload: {body}")
        
        parsed = parse_incoming(body)
        if parsed is None:
            logger.info("⚠️ Could not parse message (not a text message or malformed)")
            return
        
        phone = parsed["phone"]
        message = parsed["message"]
        message_id = parsed["message_id"]
        
        logger.info(f"✓ Parsed message from {phone}: '{message}' (ID: {message_id})")
        
        # Log inbound message to database
        from src.messenger import log_inbound
        await log_inbound(phone, message)
        
        # Route message to handler
        from src.router import route
        logger.info(f"🔀 Routing message...")
        await route(phone, message)
        
        logger.info(f"✓ Message processing completed")
        
    except Exception as e:
        logger.error(f"❌ Error handling incoming message: {type(e).__name__}: {e}", exc_info=True)
