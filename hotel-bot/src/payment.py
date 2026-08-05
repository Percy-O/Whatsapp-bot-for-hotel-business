# -*- coding: utf-8 -*-
"""
Spaxce Payment Integration — WhatsApp Bot

Handles payment processing by communicating with the Spaxce API.
The bot no longer communicates with payment providers (Paystack/Flutterwave) directly.
"""

import logging
from datetime import datetime
from src.spaxce_api_client import initialize_payment as api_initialize_payment

logger = logging.getLogger(__name__)


async def initialize_payment(
    booking_id: int,
    amount: float = None,
    email: str = None
) -> dict:
    """
    Initialize payment through Spaxce API.
    
    Args:
        booking_id: The ID of the booking in Spaxce
        amount: Optional amount to override invoice amount
        email: Guest email for payment notification
    
    Returns:
        Dict with payment_url, access_code, and reference or error
    """
    try:
        result = await api_initialize_payment(booking_id, amount, email)
        
        if result and result.get('status') == 'success':
            logger.info(f"✓ Payment initialized via Spaxce API for booking {booking_id}")
            return {
                "payment_url": result["authorization_url"],
                "access_code": result["access_code"],
                "reference": result["reference"]
            }
        else:
            error_msg = result.get('error', 'Payment initialization failed') if result else "API connection failed"
            logger.error(f"❌ Spaxce payment error: {error_msg}")
            return {"error": error_msg}
                
    except Exception as e:
        logger.error(f"❌ Payment error: {e}")
        return {"error": str(e)}


def generate_receipt(booking_data: dict, payment_data: dict, hotel_info: dict = None) -> str:
    """
    Generate booking receipt.
    """
    hotel_name = hotel_info.get('name', 'BRYBOS HOTEL') if hotel_info else 'BRYBOS HOTEL'
    hotel_phone = hotel_info.get('phone', '+2348022553182') if hotel_info else '+2348022553182'
    hotel_email = hotel_info.get('email', 'info@bryboshotel.com') if hotel_info else 'info@bryboshotel.com'

    receipt = f"""
╔════════════════════════════════════╗
║     {hotel_name.upper()} RECEIPT    ║
║         ({datetime.now().strftime('%d-%m-%Y %H:%M')})          ║
╚════════════════════════════════════╝

📋 BOOKING DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Booking Reference: {booking_data.get('reference', 'N/A')}
Guest Name: {booking_data.get('guest_name', 'Guest')}
Room Type: {booking_data.get('room_type', 'Room').title()}

📅 STAY DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Check-in: {booking_data.get('checkin', 'TBD')}
Check-out: {booking_data.get('checkout', 'TBD')}
Number of Nights: {booking_data.get('nights', 1)} night(s)

💰 AMOUNT PAID:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL AMOUNT: ₦{payment_data.get('amount', 0):,}

💳 PAYMENT DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Payment Status: ✓ COMPLETED
Reference: {payment_data.get('reference', 'N/A')}
Payment Time: {payment_data.get('paid_at', datetime.now().isoformat())}

📞 SUPPORT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reception: {hotel_phone}
Email: {hotel_email}

🎉 Thank you for choosing {hotel_name}!
We look forward to welcoming you.

Save this receipt for check-in.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return receipt
