"""
Escalation Handler — Real-Time Human Handoff
Transfers guest to hotel staff via Spaxce API.
Communicates EXCLUSIVELY via Spaxce API.
"""

import logging
import json
from datetime import datetime
from src.spaxce_api_client import get_bot_config, get_hotel_info, log_escalation

logger = logging.getLogger(__name__)


async def start(phone: str, reason: str = "Guest requested human assistance", hotel_id: int = None) -> None:
    """
    Start escalation via API.
    """
    from src.session import get_session, save_session
    from src.messenger import send_text
    
    try:
        # Get hotel config and info from API
        bot_config = await get_bot_config()
        hotel_info = await get_hotel_info()
        
        session = await get_session(phone)
        guest_name = session.get("data", {}).get("name", "Guest")
        
        logger.info(f"🔴 ESCALATION START - Guest: {phone}, Reason: {reason[:50]}")
        
        # Log escalation to Spaxce API
        # This will trigger staff notifications on the backend
        await log_escalation(
            phone=phone,
            reason=reason,
            context={
                "guest_name": guest_name,
                "session_data": session.get("data", {}),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Send confirmation to guest
        reception_contact = hotel_info.get('phone', 'our support line')
        guest_message = f"""🤝 *Connecting You Now*

We're connecting you with our team to help with your request.

*Guest Support Details:*
📞 Phone: {reception_contact}

Our team typically responds within 5-10 minutes. Thank you for your patience! 👍"""
        
        await send_text(phone, guest_message)
        
        # Update session to escalation flow
        session['flow'] = 'escalate'
        session['step'] = 'chatting'
        await save_session(phone, session)
        
        logger.info(f"✅ ESCALATION COMPLETE for {phone}")
        
    except Exception as e:
        logger.error(f"❌ Escalation error for {phone}: {e}", exc_info=True)
        # Fallback
        from src.messenger import send_text
        await send_text(phone, "Thank you for contacting us! Our team will reach out to you shortly.")


async def continue_flow(phone: str, message: str, session: dict, hotel_id: int = None) -> None:
    """
    Forward guest messages to staff during an active escalation.
    """
    from src.messenger import send_text
    from src.spaxce_api_client import log_conversation
    
    try:
        logger.info(f"📨 Forwarding escalation message from {phone} to backend...")
        
        # Log message as escalation type to the backend
        # The backend can then forward this to staff via WhatsApp/Dashboard
        await log_conversation(
            phone=phone,
            message=message,
            direction="inbound",
            message_type="escalation"
        )
        
    except Exception as e:
        logger.error(f"❌ Error in escalation continue flow: {e}")
