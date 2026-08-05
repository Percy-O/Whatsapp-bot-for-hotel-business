"""
WhatsApp Messenger — Message Sender

Sends messages out to guests via Meta WhatsApp Cloud API.
Handles text messages and logs outbound communication.

Configuration is automatically synced from Spaxce REST API.
"""

import httpx
import os
import logging
import asyncio
from src.spaxce_api_client import get_whatsapp_token, get_phone_number_id, get_hotel_info

logger = logging.getLogger(__name__)


async def send_text(phone: str, message: str) -> bool:
    """
    Send a text message via WhatsApp Cloud API.
    
    Credentials are automatically synced from Spaxce REST API.
    
    Args:
        phone: Recipient's phone number (international format)
        message: Message text to send
    
    Returns:
        True if successful, False if failed
    """
    token = await get_whatsapp_token()
    phone_id = await get_phone_number_id()
    
    if not token or not phone_id:
        logger.error(f"Missing WhatsApp credentials in Spaxce: token={bool(token)}, phone_id={bool(phone_id)}")
        return False
    
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message}
    }
    
    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"📤 Sending message to {phone} via WhatsApp API...")
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            
            logger.info(f"   Response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Message sent to {phone}")
                return True
            else:
                logger.error(f"❌ WhatsApp API error {response.status_code}: {response.text}")
                return False
    except asyncio.TimeoutError:
        logger.error(f"❌ WhatsApp API timeout for {phone}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to send message to {phone}: {type(e).__name__}: {e}")
        return False


async def send_welcome(phone: str) -> None:
    """
    Send welcome message with main menu.
    
    Hotel name is automatically synced from Spaxce REST API.
    
    Args:
        phone: Recipient's phone number
    """
    hotel_info = await get_hotel_info()
    hotel_name = hotel_info.get('name', 'Our Hotel')
    
    message = f"""👋 Welcome to {hotel_name}!

I'm your virtual assistant. How can I help you today?

Reply with a number or just tell me what you need:

1️⃣ Check room availability
2️⃣ Make a reservation
3️⃣ See room types & prices
4️⃣ General enquiries / FAQ

Or just type your question and I'll help you out! 😊"""
    
    logger.info(f"📨 Sending welcome message to {phone}")
    success = await send_text(phone, message)
    
    if success:
        logger.info(f"✅ Welcome message sent to {phone}")
        await log_outbound(phone, message, "welcome")
    else:
        logger.error(f"❌ Failed to send welcome message to {phone}")


async def log_outbound(phone: str, content: str, handler: str) -> None:
    """
    Log outbound message to Spaxce API.
    """
    from src.spaxce_api_client import log_conversation
    
    try:
        await log_conversation(
            phone=phone,
            message=content,
            direction="outbound",
            handler=handler
        )
        logger.debug(f"✓ Logged outbound message to {phone} via API")
    except Exception as e:
        logger.error(f"❌ Failed to log outbound message via API: {e}")


async def log_inbound(phone: str, content: str) -> None:
    """
    Log inbound message to Spaxce API.
    """
    from src.spaxce_api_client import log_conversation
    
    try:
        await log_conversation(
            phone=phone,
            message=content,
            direction="inbound",
            handler="whatsapp_webhook"
        )
        logger.debug(f"✓ Logged inbound message from {phone} via API")
    except Exception as e:
        logger.error(f"❌ Failed to log inbound message via API: {e}")
