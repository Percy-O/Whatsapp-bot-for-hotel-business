# -*- coding: utf-8 -*-
"""
Booking Conversation Handler — Multi-Step Booking Flow

Manages conversational booking flow:
1. List room types
2. Check availability
3. Collect guest info
4. Confirm booking
5. Generate payment link

Works with spaxce_api_client.py to create real bookings in Spaxce.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from src.spaxce_api_client import (
    get_room_types_list,
    check_availability,
    create_booking,
    get_booking,
)

logger = logging.getLogger(__name__)


class BookingState:
    """Track booking conversation state."""
    
    def __init__(self):
        self.step = "START"  # START, ROOM_SELECTED, DATES_CONFIRMED, COLLECTING_INFO, BOOKING_CREATED, COMPLETED
        self.room_types = []
        self.selected_room_type = None
        self.check_in = None
        self.check_out = None
        self.availability = None
        self.guest_info = {
            "first_name": None,
            "last_name": None,
            "email": None,
            "phone": None,
            "num_guests": None,
            "special_requests": None,
        }
        self.booking_id = None
        self.booking = None
    
    def to_dict(self) -> Dict:
        """Convert state to dict for session storage."""
        return {
            "step": self.step,
            "room_types": self.room_types,
            "selected_room_type": self.selected_room_type,
            "check_in": self.check_in,
            "check_out": self.check_out,
            "availability": self.availability,
            "guest_info": self.guest_info,
            "booking_id": self.booking_id,
            "booking": self.booking,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "BookingState":
        """Create state from dict."""
        state = cls()
        state.step = data.get("step", "START")
        state.room_types = data.get("room_types", [])
        state.selected_room_type = data.get("selected_room_type")
        state.check_in = data.get("check_in")
        state.check_out = data.get("check_out")
        state.availability = data.get("availability")
        state.guest_info = data.get("guest_info", {})
        state.booking_id = data.get("booking_id")
        state.booking = data.get("booking")
        return state


def parse_date(date_str: str) -> Optional[str]:
    """
    Parse date string in DD/MM/YYYY or ISO format.
    
    Args:
        date_str: Date string (DD/MM/YYYY or YYYY-MM-DD)
    
    Returns:
        ISO format string or None
    """
    try:
        # Try DD/MM/YYYY format
        if "/" in date_str:
            dt = datetime.strptime(date_str, "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        # Try ISO format
        elif "-" in date_str:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        else:
            return None
    except ValueError:
        return None


def format_date_display(date_str: str) -> str:
    """Format date for display (DD/MM/YYYY)."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except:
        return date_str


async def handle_booking_step(
    phone: str,
    message: str,
    state_dict: Optional[Dict] = None
) -> tuple[str, Dict]:
    """
    Handle next step in booking conversation.
    
    Args:
        phone: Guest phone number
        message: Guest message
        state_dict: Current booking state (from session)
    
    Returns:
        (response_message, updated_state_dict)
    """
    
    # Restore or create state
    state = BookingState.from_dict(state_dict or {})
    
    logger.info(f"🤖 Booking Handler - Step: {state.step}, Message: {message[:50]}")
    
    try:
        # ===== STEP 1: START - Greet and ask for room preference =====
        if state.step == "START":
            logger.info("📍 Starting booking process")
            
            # Fetch room types
            room_types = await get_room_types_list()
            if not room_types:
                return "❌ Sorry, I'm having trouble accessing our room types. Let me connect you with our team.", state.to_dict()
            
            state.room_types = room_types
            state.step = "SHOWING_ROOMS"
            
            # Build room list message
            msg_parts = ["🏨 Welcome! Here are our available room types:\n"]
            for i, room in enumerate(room_types, 1):
                name = room.get('name', 'Room')
                price = room.get('price_per_night', 0)
                capacity = room.get('capacity', 1)
                amenities = ', '.join(room.get('amenities_list', [])[:3])
                msg_parts.append(f"\n{i}. {name}")
                msg_parts.append(f"   • Price: ₦{int(price):,}/night")
                msg_parts.append(f"   • Capacity: {capacity} guests")
                if amenities:
                    msg_parts.append(f"   • Amenities: {amenities}")
            
            msg_parts.append("\n\n👉 Which room interests you? (Reply with room name or number)")
            return "".join(msg_parts), state.to_dict()
        
        # ===== STEP 2: SHOWING_ROOMS - User selects a room =====
        elif state.step == "SHOWING_ROOMS":
            logger.info(f"📍 User selecting room: {message}")
            
            message_lower = message.lower().strip()
            selected_room = None
            
            # Try to match by room name or number
            for i, room in enumerate(state.room_types, 1):
                room_name = room.get('name', '').lower()
                if message_lower == str(i) or message_lower == room_name or room_name in message_lower:
                    selected_room = room
                    break
            
            if not selected_room:
                return "❌ I didn't recognize that room. Please reply with the room number (1, 2, 3...) or name from the list above.", state.to_dict()
            
            state.selected_room_type = selected_room
            state.step = "ASKING_DATES"
            
            room_name = selected_room.get('name', 'Room')
            price = selected_room.get('price_per_night', 0)
            
            return f"✅ Great! You've selected {room_name} (₦{int(price):,}/night)\n\n📅 When would you like to check in? Please use DD/MM/YYYY format (e.g., 05/04/2026)", state.to_dict()
        
        # ===== STEP 3: ASKING_DATES - Collect check-in date =====
        elif state.step == "ASKING_DATES":
            logger.info(f"📍 Parsing check-in date: {message}")
            
            check_in = parse_date(message)
            if not check_in:
                return "❌ I didn't understand that date. Please use DD/MM/YYYY format (e.g., 05/04/2026)", state.to_dict()
            
            # Validate date is not in the past
            try:
                dt = datetime.strptime(check_in, "%Y-%m-%d")
                if dt.date() < datetime.now().date():
                    return "❌ Check-in date must be in the future. Please choose a different date.", state.to_dict()
            except:
                return "❌ Invalid date. Please try again in DD/MM/YYYY format.", state.to_dict()
            
            state.check_in = check_in
            state.step = "ASKING_CHECKOUT"
            
            check_in_display = format_date_display(check_in)
            return f"✅ Check-in: {check_in_display}\n\n📅 When will you check out? (DD/MM/YYYY format)", state.to_dict()
        
        # ===== STEP 4: ASKING_CHECKOUT - Collect check-out date =====
        elif state.step == "ASKING_CHECKOUT":
            logger.info(f"📍 Parsing check-out date: {message}")
            
            check_out = parse_date(message)
            if not check_out:
                return "❌ I didn't understand that date. Please use DD/MM/YYYY format.", state.to_dict()
            
            # Validate checkout is after checkin
            if check_out <= state.check_in:
                return "❌ Check-out date must be after check-in date. Please try again.", state.to_dict()
            
            state.check_out = check_out
            state.step = "CHECKING_AVAILABILITY"
            
            # Check availability
            logger.info(f"🔍 Checking availability: Room {state.selected_room_type.get('id')}, {state.check_in} to {check_out}")
            
            availability = await check_availability(
                room_type_id=state.selected_room_type.get('id'),
                check_in=state.check_in,
                check_out=check_out
            )
            
            if not availability:
                return "❌ I couldn't check availability for those dates. Let me connect you with our team.", state.to_dict()
            
            state.availability = availability
            
            # Check if rooms are available
            if not availability.get('is_available'):
                available_dates = availability.get('next_available_date')
                if available_dates:
                    msg = f"❌ Sorry, that room is fully booked for those dates.\n\n📅 Next available: {format_date_display(available_dates)}\n\nWould you like to book those dates instead?"
                else:
                    msg = "❌ Sorry, that room is not available for those dates. Please choose different dates."
                state.step = "ASKING_DATES"
                return msg, state.to_dict()
            
            # Show pricing and ask to confirm
            state.step = "CONFIRMING_BOOKING"
            
            check_in_display = format_date_display(state.check_in)
            check_out_display = format_date_display(check_out)
            room_name = state.selected_room_type.get('name', 'Room')
            price = availability.get('total_price', availability.get('price_per_night', 0))
            subtotal = availability.get('subtotal', 0)
            tax = availability.get('tax', 0)
            
            msg_parts = [
                "✅ Great news! Room is available!\n",
                f"🏨 {room_name}\n",
                f"📅 {check_in_display} → {check_out_display}\n",
                f"💰 Subtotal: ₦{int(subtotal):,}\n",
                f"💰 Tax: ₦{int(tax):,}\n",
                f"💰 **Total: ₦{int(price):,}**\n\n",
                "👉 Ready to proceed? Reply YES to continue with your guest info."
            ]
            
            return "".join(msg_parts), state.to_dict()
        
        # ===== STEP 5: CONFIRMING_BOOKING - User confirms price =====
        elif state.step == "CONFIRMING_BOOKING":
            logger.info(f"📍 User confirming booking")
            
            if message.lower().strip() not in ['yes', 'yeah', 'confirm', 'ok', 'sure']:
                return "❌ I didn't catch that. Reply YES to confirm or NO to cancel.", state.to_dict()
            
            state.step = "COLLECTING_FIRSTNAME"
            return "👤 What's your first name?", state.to_dict()
        
        # ===== STEP 6-10: Collect guest information =====
        elif state.step == "COLLECTING_FIRSTNAME":
            state.guest_info['first_name'] = message.strip()
            state.step = "COLLECTING_LASTNAME"
            return "👤 And your last name?", state.to_dict()
        
        elif state.step == "COLLECTING_LASTNAME":
            state.guest_info['last_name'] = message.strip()
            state.step = "COLLECTING_EMAIL"
            return "📧 Your email address?", state.to_dict()
        
        elif state.step == "COLLECTING_EMAIL":
            email = message.strip()
            if '@' not in email:
                return "❌ Please enter a valid email address.", state.to_dict()
            state.guest_info['email'] = email
            state.step = "COLLECTING_PHONE"
            return "📱 Your phone number?", state.to_dict()
        
        elif state.step == "COLLECTING_PHONE":
            phone_input = message.strip()
            state.guest_info['phone'] = phone_input
            state.step = "COLLECTING_GUESTS"
            return "👥 How many guests will be staying?", state.to_dict()
        
        elif state.step == "COLLECTING_GUESTS":
            try:
                num_guests = int(message.strip())
                if num_guests < 1:
                    return "❌ Please enter a number ≥ 1.", state.to_dict()
                state.guest_info['num_guests'] = num_guests
                state.step = "COLLECTING_REQUESTS"
                return "✨ Any special requests? (or reply 'none')", state.to_dict()
            except ValueError:
                return "❌ Please enter a number (1, 2, 3...)", state.to_dict()
        
        elif state.step == "COLLECTING_REQUESTS":
            requests = message.strip()
            if requests.lower() != 'none':
                state.guest_info['special_requests'] = requests
            state.step = "CREATING_BOOKING"
            
            # Create the booking in Spaxce
            logger.info(f"📍 Creating booking in Spaxce")
            
            # Combine names for backend
            guest_name = f"{state.guest_info['first_name']} {state.guest_info['last_name']}".strip()
            
            booking_data = {
                'room_id': state.selected_room_type.get('id'), # API expects room_id
                'check_in_date': state.check_in,
                'check_out_date': state.check_out,
                'guest_name': guest_name,
                'guest_email': state.guest_info['email'],
                'guest_phone': state.guest_info['phone'] or phone,
                'number_of_guests': state.guest_info['num_guests'],
                'special_requests': state.guest_info.get('special_requests', ''),
            }
            
            booking_res = await create_booking(booking_data)
            
            if not booking_res or not booking_res.get('success'):
                return "❌ Sorry, I'm having trouble creating your booking. Let me connect you with our team.", state.to_dict()
            
            booking = booking_res.get('booking', {})
            state.booking = booking
            state.booking_id = booking.get('id')
            state.step = "BOOKING_CREATED"
            
            # Initialize payment via API to get Paystack link
            logger.info(f"📍 Initializing payment for booking {state.booking_id}")
            from src.spaxce_api_client import initialize_payment
            
            payment = await initialize_payment(
                booking_id=state.booking_id,
                email=state.guest_info['email'],
                amount=float(booking.get('total_price', 0))
            )
            
            payment_link = payment.get('payment_url') if payment else None
            
            # Generate confirmation message
            booking_ref = booking.get('booking_id', 'N/A')
            total = booking.get('total_price', 0)
            
            msg_parts = [
                "🎉 *BOOKING CREATED!*\n\n",
                f"✅ Reference: *{booking_ref}*\n",
                f"👤 Guest: {guest_name}\n",
                f"🏨 Room: {state.selected_room_type.get('name', 'Room')}\n",
                f"📅 Stay: {format_date_display(state.check_in)} → {format_date_display(state.check_out)}\n",
                f"💰 Total: *₦{float(total):,.0f}*\n",
            ]
            
            if payment_link:
                msg_parts.append(f"\n💳 *Complete your payment here:*\n{payment_link}\n")
                msg_parts.append("\nYour booking will be confirmed automatically once payment is received. 👍")
            else:
                msg_parts.append("\nOur team will contact you shortly with payment details to confirm your stay. 🙌")
            
            return "".join(msg_parts), state.to_dict()
        
        else:
            return "❌ Unknown booking state. Please try again.", state.to_dict()
    
    except Exception as e:
        logger.error(f"❌ Booking handler error: {e}")
        return f"❌ Booking error: {str(e)[:100]}", state.to_dict()


async def should_start_booking(message: str) -> bool:
    """
    Detect if user wants to start booking process.
    
    Args:
        message: User message
    
    Returns:
        True if user wants to book
    """
    booking_keywords = [
        'book', 'booking', 'reserve', 'reservation', 'room',
        'rooms', 'stay', 'check in', 'checkin', 'night',
        'nights', 'how much', 'price', 'cost', 'availability',
        'available', 'when', 'dates', 'booking?'
    ]
    
    message_lower = message.lower().strip()
    return any(keyword in message_lower for keyword in booking_keywords)


async def reset_booking_state() -> Dict:
    """Reset booking state."""
    return BookingState().to_dict()
