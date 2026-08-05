"""
FAQ Handler — Frequently Asked Questions

Matches keywords to pre-written FAQ answers from Spaxce Knowledge Base.
Communicates EXCLUSIVELY via Spaxce API.
"""

import json
import logging
from src.spaxce_api_client import get_bot_config, get_hotel_info

logger = logging.getLogger(__name__)

KEYWORD_MAP = {
    "wifi": ["wifi", "wi-fi", "internet", "network", "password"],
    "breakfast": ["breakfast", "food", "eat", "meal", "dining", "restaurant"],
    "parking": ["parking", "park", "car", "vehicle", "garage"],
    "cancellation": ["cancel", "cancellation", "refund", "money back"],
    "payment": ["payment", "pay", "transfer", "card", "cash", "pos", "bank"],
    "address": ["address", "location", "directions", "how to get", "where", "map"],
    "pool": ["pool", "swimming", "swim"],
    "gym": ["gym", "fitness", "workout", "exercise"],
    "early_checkin": ["early", "late checkout", "late check-out", "check in early"],
    "reception": ["contact", "reception", "call", "phone number", "reach you"]
}


async def answer(phone: str, message: str, hotel_id: int = None) -> None:
    """
    Find matching FAQ and send answer via API.
    """
    from src.messenger import send_text, log_outbound
    from src.session import get_session
    
    msg_lower = message.lower()
    session = await get_session(phone)
    
    # 1. Try to find matching FAQ topic from keywords
    matched_topic = None
    for topic, keywords in KEYWORD_MAP.items():
        if any(k in msg_lower for k in keywords):
            matched_topic = topic
            break
    
    # 2. Fetch hotel config and info from API
    bot_config = await get_bot_config()
    hotel_info = await get_hotel_info()
    
    # 3. Extract FAQ from knowledge base
    faq_data = {}
    kb_json = bot_config.get('knowledge_base')
    if kb_json:
        try:
            faq_data = json.loads(kb_json) if isinstance(kb_json, str) else kb_json
        except:
            logger.warning("⚠️ Failed to parse knowledge_base JSON")
            
    if matched_topic and matched_topic in faq_data:
        # found direct match in knowledge base
        reply = faq_data[matched_topic] + "\n\nIs there anything else I can help you with? 😊"
    elif matched_topic:
        # Topic matched but no text in KB, give fallback
        phone_contact = hotel_info.get('phone', '+2348022553182')
        reply = f"I'm sorry, I don't have the specific details for that right now. Please contact our reception at {phone_contact} for assistance. ☎️"
    else:
        # No keyword match, fallback to AI agent
        from src.agent import ask
        await ask(phone, message, session, hotel_id)
        return
    
    # Send answer
    await send_text(phone, reply)
    await log_outbound(phone, reply, "faq")


async def start(phone: str, hotel_id: int = None) -> None:
    """
    Send FAQ topic menu.
    """
    from src.messenger import send_text, log_outbound
    
    message = """Here are some things I can help you with:

• 🌐 WiFi & internet
• 🍽️ Breakfast & dining
• 🅿️ Parking
• 💰 Cancellation & refunds
• 💳 Payment methods
• 📍 Address & directions
• 🏊 Swimming pool
• 💪 Gym & fitness
• ⏰ Early check-in / late check-out
• 📞 Reception contact

Just type your question and I'll answer it! 😊"""
    
    await send_text(phone, message)
    await log_outbound(phone, message, "faq_menu")
