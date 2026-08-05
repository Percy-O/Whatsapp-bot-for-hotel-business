"""
Booking Handler — API-Driven Room Reservations
Multi-step booking flow using Spaxce REST API.
Communicates EXCLUSIVELY via Spaxce API.
"""

import logging
from src.booking_handler import BookingState, handle_booking_step

logger = logging.getLogger(__name__)


async def start(phone: str, hotel_id: int = None) -> None:
    """
    Start booking flow via API.
    """
    from src.session import get_session, save_session
    from src.messenger import send_text
    
    # Initialize booking state in session
    session = await get_session(phone)
    session["flow"] = "booking"
    session["booking_state"] = BookingState().to_dict()
    await save_session(phone, session)
    
    # Delegate to the specialized booking handler to show the first step (room list)
    msg, updated_state = await handle_booking_step(phone, "START", session["booking_state"])
    
    session["booking_state"] = updated_state
    await save_session(phone, session)
    
    await send_text(phone, msg)


async def continue_flow(phone: str, message: str, session: dict, hotel_id: int = None) -> None:
    """
    Continue booking flow via API-driven state machine.
    """
    from src.session import save_session, clear_session
    from src.messenger import send_text
    
    # Get current state
    booking_state = session.get("booking_state", {})
    
    try:
        # Process step
        response, updated_state = await handle_booking_step(phone, message, booking_state)
        
        # Update session
        session["booking_state"] = updated_state
        await save_session(phone, session)
        
        # Send response
        await send_text(phone, response)
        
        # If booking is completed, clear flow
        if updated_state.get("step") == "BOOKING_CREATED":
            await clear_session(phone)
            logger.info(f"✅ Booking process completed for {phone}")
            
    except Exception as e:
        logger.error(f"❌ Error in booking flow for {phone}: {e}", exc_info=True)
        await send_text(phone, "❌ Sorry, I encountered an error processing your booking. Let me connect you with our support team.")
        from src.handlers.escalate import start as escalate_start
        await escalate_start(phone, f"Booking flow error: {e}")
