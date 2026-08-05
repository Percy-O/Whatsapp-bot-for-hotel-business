# -*- coding: utf-8 -*-
"""
Booking Search Handler — Retrieve Booking

Allows customers to search and retrieve their booking details
by reference number via Spaxce API.
Communicates EXCLUSIVELY via Spaxce API.
"""

import logging
from datetime import datetime
from src.spaxce_api_client import lookup_booking, get_hotel_info

logger = logging.getLogger(__name__)


async def search_booking(phone: str, booking_ref: str, hotel_id: int = None) -> None:
    """
    Search for booking by reference and send details to customer via API.
    """
    from src.messenger import send_text
    from src.payment import generate_receipt
    
    try:
        # Normalize reference
        booking_ref = booking_ref.strip().upper()
        
        # Validate format
        if not booking_ref.startswith("HTL-"):
            await send_text(phone, "❌ Invalid booking reference format.\n\nFormat: HTL-YYYYMMDD-XXXX\nExample: HTL-20260317-1234")
            return
        
        logger.info(f"🔍 Searching booking via API: {booking_ref}")
        
        # Get booking from API
        booking = await lookup_booking(booking_ref)
        
        if not booking:
            await send_text(phone, f"❌ Booking reference not found: {booking_ref}\n\nPlease check the reference and try again.")
            return
        
        # Get hotel info for contact details
        hotel_info = await get_hotel_info()
        
        # Format booking details
        checkin = booking.get("check_in")
        checkout = booking.get("check_out")
        
        # Calculate nights from ISO strings
        try:
            d1 = datetime.fromisoformat(checkin)
            d2 = datetime.fromisoformat(checkout)
            nights = (d2 - d1).days
        except:
            nights = 1
            
        status = booking.get("payment_status", "pending").upper()
        status_emoji = "✅" if status == "COMPLETED" else "⏳"
        
        # Build booking details message
        details = f"""{status_emoji} *BOOKING DETAILS*

Reference: *{booking_ref}*
Guest Name: {booking.get('guest_name')}
Room Type: {booking.get('room_type', 'N/A').upper()}
Room Number: {booking.get('room_number', 'N/A')}

📅 *STAY DETAILS:*
Check-in: {format_date_readable(checkin)}
Check-out: {format_date_readable(checkout)}
Nights: {nights}

💰 *PAYMENT:*
Total Amount: ₦{float(booking.get('total_price', 0)):,.0f}
Status: {status}

🎫 *PRESENTATION CODE:*
Show this reference to the reception:
*{booking_ref}*

Need help? 
📞 Call: {hotel_info.get('phone', '+2348022553182')}
📧 Email: {hotel_info.get('email', 'info@spaxce.com')}"""
        
        await send_text(phone, details)
        
        # If payment is completed, also send the receipt
        if status == "COMPLETED":
            receipt_data = {
                "reference": booking_ref,
                "guest_name": booking.get("guest_name"),
                "room_type": booking.get("room_type"),
                "room_number": booking.get("room_number"),
                "checkin": checkin,
                "checkout": checkout,
                "nights": nights,
                "guests": 1,
                "price_per_night": float(booking.get("total_price", 0)) // max(1, nights),
                "subtotal": float(booking.get("total_price", 0))
            }
            
            payment_data = {
                "amount": float(booking.get("total_price", 0)),
                "method": "API-Internal",
                "reference": booking_ref,
                "paid_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            
            receipt = generate_receipt(receipt_data, payment_data)
            await send_text(phone, receipt)
        
        logger.info(f"✓ Booking details sent: {booking_ref}")
        
    except Exception as e:
        logger.error(f"❌ Error searching booking: {e}", exc_info=True)
        await send_text(phone, "❌ Error retrieving booking. Please try again or contact our support.")


def format_date_readable(date_str: str) -> str:
    """Convert ISO date to readable format."""
    try:
        # Handle ISO with T or space
        clean_date = date_str.split('T')[0] if 'T' in date_str else date_str
        date_obj = datetime.strptime(clean_date, "%Y-%m-%d")
        return date_obj.strftime("%A %d %B %Y")
    except:
        return date_str
