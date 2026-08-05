"""
Availability Handler — Room Availability Search

Multi-step handler to check room availability for a date range via Spaxce API.
Communicates EXCLUSIVELY via Spaxce API.
"""

import dateparser
import logging
from datetime import datetime
from src.spaxce_api_client import get_room_types_list, check_availability

logger = logging.getLogger(__name__)


def format_date_readable(date_str: str) -> str:
    """Convert ISO date to readable format."""
    try:
        clean_date = date_str.split('T')[0] if 'T' in date_str else date_str
        date_obj = datetime.strptime(clean_date, "%Y-%m-%d")
        return date_obj.strftime("%A %d %B %Y")
    except:
        return date_str


async def start(phone: str, hotel_id: int = None) -> None:
    """
    Start availability check flow via API.
    """
    from src.session import get_session, save_session
    from src.messenger import send_text
    
    # Initialize session
    session = await get_session(phone)
    session["flow"] = "availability"
    session["step"] = "awaiting_checkin_date"
    session["data"] = {}
    await save_session(phone, session)
    
    message = "Great! Let's check what's available for your stay. 📅\n\n" \
             "What is your *check-in* date? (e.g. tomorrow, 25th March, 25/03)"
    
    await send_text(phone, message)


async def continue_flow(phone: str, message: str, session: dict, hotel_id: int = None) -> None:
    """
    Continue availability flow through multi-step process.
    """
    from src.session import save_session
    from src.messenger import send_text
    
    step = session.get("step")
    
    if step == "awaiting_checkin_date":
        parsed = dateparser.parse(message, settings={"PREFER_DATES_FROM": "future"})
        
        if not parsed:
            await send_text(phone, "Sorry, I didn't recognize that date. Please try again (e.g. '25th March' or '25/03')")
            return
        
        checkin = parsed.strftime("%Y-%m-%d")
        session["data"]["checkin"] = checkin
        session["step"] = "awaiting_checkout_date"
        await save_session(phone, session)
        
        await send_text(phone, f"Got it — check-in on *{format_date_readable(checkin)}*. \n\nWhen would you like to *check-out*?")
    
    elif step == "awaiting_checkout_date":
        parsed = dateparser.parse(message, settings={"PREFER_DATES_FROM": "future"})
        
        if not parsed:
            await send_text(phone, "I didn't catch that date. Please enter your check-out date.")
            return
        
        checkout = parsed.strftime("%Y-%m-%d")
        checkin = session["data"].get("checkin")
        
        if checkout <= checkin:
            await send_text(phone, "Check-out must be after check-in. Please pick a later date.")
            return
        
        session["data"]["checkout"] = checkout
        session["step"] = "awaiting_room_type"
        await save_session(phone, session)
        
        # Fetch room types from API to show options
        room_types = await get_room_types_list()
        
        if not room_types:
            await send_text(phone, "We're having trouble loading our room types. Let me just check all available rooms for those dates...")
            await check_and_reply(phone, session)
            return
            
        menu = "Which type of room are you looking for?\n\n"
        for i, rt in enumerate(room_types, 1):
            menu += f"{i}️⃣ *{rt['name'].upper()}*\n"
            
        menu += f"{len(room_types)+1}️⃣ Show all available"
        
        # Store room types in session for mapping
        session["data"]["room_types_cache"] = {str(i+1): rt['id'] for i, rt in enumerate(room_types)}
        await save_session(phone, session)
        
        await send_text(phone, menu)
    
    elif step == "awaiting_room_type":
        msg_strip = message.strip()
        room_types_cache = session["data"].get("room_types_cache", {})
        
        room_type_id = room_types_cache.get(msg_strip)
        
        # If not a number, try to match by name
        if not room_type_id:
            room_types = await get_room_types_list()
            for rt in room_types:
                if rt['name'].lower() in msg_strip.lower():
                    room_type_id = rt['id']
                    break
        
        session["data"]["room_type_id"] = room_type_id
        session["step"] = None
        session["flow"] = None
        
        await check_and_reply(phone, session)


async def check_and_reply(phone: str, session: dict) -> None:
    """
    Query Spaxce API for availability and reply.
    """
    from src.messenger import send_text
    from src.session import clear_session
    
    checkin = session["data"].get("checkin")
    checkout = session["data"].get("checkout")
    room_type_id = session["data"].get("room_type_id")
    
    logger.info(f"🔍 Checking API availability: {checkin} to {checkout}, Room ID: {room_type_id}")
    
    # If room_type_id is 5 (Show all) or not specified, we'll iterate or just fetch summary
    # The API check_availability currently takes a room_type_id
    
    if not room_type_id:
        # User wants to see all. We iterate through room types
        room_types = await get_room_types_list()
        results = []
        for rt in room_types:
            avail = await check_availability(rt['id'], checkin, checkout)
            if avail and avail.get('available'):
                results.append(avail)
        
        if not results:
            reply = f"I'm sorry, we don't have any rooms available from {format_date_readable(checkin)} to {format_date_readable(checkout)}. Try different dates? 😊"
            await send_text(phone, reply)
            await clear_session(phone)
            return
            
        message = f"✅ We have availability for your stay!\n\n"
        for res in results:
            rt = res['room_type']
            pricing = res['pricing']
            message += f"🏨 *{rt['name'].upper()}*\n"
            message += f"💰 ₦{float(pricing['total']):,.0f} total\n"
            message += f"🛏 {res['available_count']} rooms left\n\n"
            
        message += "To book any of these, reply *2* to start a formal booking."
    else:
        # Check specific room type
        res = await check_availability(room_type_id, checkin, checkout)
        
        if not res or not res.get('available'):
            reply = f"I'm sorry, that room type is not available for those dates. Try different dates or a different room type? 😊"
            await send_text(phone, reply)
            await clear_session(phone)
            return
            
        rt = res['room_type']
        pricing = res['pricing']
        message = f"✅ *{rt['name'].upper()}* is available!\n\n"
        message += f"📅 Stay: {format_date_readable(checkin)} — {format_date_readable(checkout)}\n"
        message += f"💰 Total: *₦{float(pricing['total']):,.0f}*\n"
        message += f"🛏 Available: {res['available_count']} rooms\n\n"
        message += "Would you like to book this? Reply *2* to proceed."
    
    await send_text(phone, message)
    await clear_session(phone)
