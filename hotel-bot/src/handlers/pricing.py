"""
Pricing Handler — Room Price List

Displays all available room types with amenities and pricing from Spaxce API.
Communicates EXCLUSIVELY via Spaxce API.
"""

import logging
from src.spaxce_api_client import get_room_types_list, get_hotel_info

logger = logging.getLogger(__name__)


def format_naira(amount: float) -> str:
    """Format amount as Nigerian Naira."""
    try:
        val = float(amount)
        return f"₦{val:,.0f}"
    except (ValueError, TypeError):
        return f"₦{amount}"


async def start(phone: str, hotel_id: int = None) -> None:
    """
    Send pricing list with all room types via API.
    """
    from src.messenger import send_text, log_outbound
    
    try:
        # Fetch data from API
        hotel_info = await get_hotel_info()
        rooms = await get_room_types_list()
        
        hotel_name = hotel_info.get("name", "Hotel")
        
        # Build price list message
        message = f"🏨 *{hotel_name.upper()} — Room Types & Rates*\n\n"
        
        if not rooms:
            message += "I'm sorry, no room pricing is currently available. Please contact our reception.\n\n"
        else:
            for room in rooms:
                room_name = room.get("name", "Room Type")
                price = room.get("price_per_night", 0)
                capacity = room.get("capacity", 0)
                description = room.get("description", "")
                
                # Amenities might be a list or a comma-separated string
                amenities_data = room.get("amenities", [])
                if isinstance(amenities_data, list):
                    amenities = ", ".join(amenities_data[:4])
                else:
                    amenities = str(amenities_data)
                
                message += f"🛏 *{room_name.upper()}*\n"
                message += f"{format_naira(price)} per night · Up to {capacity} guests\n"
                if description:
                    message += f"{description}\n"
                if amenities:
                    message += f"Amenities: {amenities}\n"
                message += "\n"
        
        message += "To check availability, reply *1*\n"
        message += "To make a booking, reply *2*"
        
        # Send message
        await send_text(phone, message)
        await log_outbound(phone, message, "pricing")
        
    except Exception as e:
        logger.error(f"Error in pricing handler: {e}")
        await send_text(phone, "Sorry, I couldn't load the pricing information right now. Please try again or call our reception.")
