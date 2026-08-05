"""
Intent Router — Message Dispatcher

Analyzes incoming messages to determine which handler should respond.
Communicates EXCLUSIVELY via Spaxce API.
Follows priority order: greeting → menu → booking search → keywords → AI.
"""

import logging
import re
import os
from src.spaxce_api_client import get_bot_config_by_phone, get_bot_config

logger = logging.getLogger(__name__)


async def route(phone: str, message: str) -> None:
    """
    Route incoming message to appropriate handler.
    
    Uses Spaxce API to:
    1. Identify hotel from WhatsApp number
    2. Manage session state
    3. Retrieve dynamic content
    """
    from src.session import get_session, is_session_expired, clear_session
    from src.messenger import send_welcome
    
    logger.info(f"📍 Routing message from {phone}...")
    
    # === STEP 1: Identify hotel from WhatsApp number ===
    # In production, the bot's own WhatsApp number is used to identify the hotel
    bot_phone = os.getenv("BOT_WHATSAPP_NUMBER")
    
    # Fetch config from API (this identifies the hotel and its settings)
    hotel_config = await get_bot_config()
    
    if not hotel_config:
        logger.error(f"❌ No active bot configuration found for this instance")
        return
        
    hotel_id = hotel_config.get('hotel_id')
    logger.info(f"✓ Hotel identified via API: {hotel_config.get('hotel_name')} (ID: {hotel_id})")
    
    # Load session (async)
    session = await get_session(phone)
    session['hotel_id'] = hotel_id
    
    # Check if expired
    if is_session_expired(session):
        logger.info(f"   Session expired, clearing")
        await clear_session(phone)
        session = await get_session(phone)
        session['hotel_id'] = hotel_id
    
    # Normalize message
    msg = message.lower().strip()
    
    # ===== PRIORITY 1: RESET FLOW ON GREETING =====
    greetings = ["hi", "hello", "hey", "start", "good morning", "good afternoon", "good evening"]
    if any(g == msg for g in greetings) or msg == "menu":
        logger.info(f"   ✓ Greeting detected, showing menu")
        await clear_session(phone)
        await send_welcome(phone, hotel_id)
        return
    
    # ===== PRIORITY 2: CHECK BOOKING REFERENCE =====
    booking_ref_pattern = r"HTL-\d{8}-\d{4}"
    if re.match(booking_ref_pattern, message.strip().upper()):
        from src.handlers.search_booking import search_booking
        await search_booking(phone, message.strip(), hotel_id)
        return
    
    # ===== PRIORITY 3: CONTINUE ACTIVE FLOW =====
    if session.get("flow"):
        await continue_flow(phone, message, session, hotel_id)
        return
    
    # ===== PRIORITY 4: MENU SELECTION =====
    if msg == "1":
        from src.handlers.availability import start as availability_start
        await availability_start(phone, hotel_id)
        return
    if msg == "2":
        from src.handlers.booking import start as booking_start
        await booking_start(phone, hotel_id)
        return
    if msg == "3":
        from src.handlers.pricing import start as pricing_start
        await pricing_start(phone, hotel_id)
        return
    if msg == "4":
        from src.handlers.faq import start as faq_start
        await faq_start(phone, hotel_id)
        return
    
    # ===== PRIORITY 5: ESCALATION KEYWORDS =====
    real_escalation_keywords = ["complaint", "emergency", "urgent", "problem", "manager", "refund"]
    if any(k in msg for k in real_escalation_keywords):
        from src.handlers.escalate import start as escalate_start
        await escalate_start(phone, reason=message, hotel_id=hotel_id)
        return
    
    # ===== PRIORITY 6: FALLBACK TO AI =====
    logger.info(f"   → Routing to AI handler")
    from src.agent import ask
    await ask(phone, message, session, hotel_id)


async def continue_flow(phone: str, message: str, session: dict, hotel_id: int) -> None:
    """Continue an active multi-step flow."""
    flow = session.get("flow")
    
    try:
        if flow == "booking":
            from src.handlers.booking import continue_flow as booking_continue
            await booking_continue(phone, message, session, hotel_id)
        elif flow == "availability":
            from src.handlers.availability import continue_flow as availability_continue
            await availability_continue(phone, message, session, hotel_id)
        elif flow == "escalate":
            from src.handlers.escalate import continue_flow as escalate_continue
            await escalate_continue(phone, message, session, hotel_id)
        else:
            logger.warning(f"Unknown flow: {flow}")
            from src.handlers.escalate import start as escalate_start
            await escalate_start(phone, f"Session lost: {flow}", hotel_id=hotel_id)
    except Exception as e:
        logger.error(f"Error in {flow} flow: {e}")
        from src.handlers.escalate import start as escalate_start
        await escalate_start(phone, f"Error in process: {type(e).__name__}", hotel_id=hotel_id)

