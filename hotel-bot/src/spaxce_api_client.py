# -*- coding: utf-8 -*-
"""
Spaxce API Client —  Hotel Bot Integration

Uses HTTP/REST API to communicate with Spaxce instead of direct database access.
Provides secure, scalable, and professional communication between bot and Spaxce.
"""

import httpx
import os
import logging
from typing import Optional, Dict, Any, List
from functools import lru_cache
import asyncio

logger = logging.getLogger(__name__)


class SpaxceAPIClient:
    """
    HTTP client for communicating with Spaxce API.
    
    Handles authentication, request/response, caching, and error handling.
    """
    
    def __init__(self):
        """Initialize API client with Spaxce server details."""
        self.base_url = os.getenv('SPAXCE_API_URL', 'http://localhost:8000').rstrip('/')
        self.api_token = os.getenv('SPAXCE_API_TOKEN', '')
        self.timeout = int(os.getenv('SPAXCE_API_TIMEOUT', 10))
        self.cache_ttl = int(os.getenv('SPAXCE_CACHE_TTL', 300))
        
        if not self.api_token:
            logger.warning('⚠️ SPAXCE_API_TOKEN not set in .env')
        
        # Cache for storing config
        self._config_cache = None
        self._cache_time = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication."""
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_token}',
            'User-Agent': 'HotelBot/1.0'
        }
    
    def _is_cache_valid(self) -> bool:
        """Check if cached config is still valid."""
        if not self._config_cache or not self._cache_time:
            return False
        
        import time
        return (time.time() - self._cache_time) < self.cache_ttl
    
    async def health_check(self) -> bool:
        """
        Check if Spaxce API is accessible.
        
        Returns: True if API is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/bot/config/health/',
                    headers=self._get_headers()
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f'❌ Spaxce API health check failed: {e}')
            return False
    
    async def get_bot_config(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetch bot configuration from Spaxce API.
        
        Args:
            force_refresh: Force fetch from API, bypass cache
        
        Returns:
            Bot configuration dict with all settings, or None if error
        """
        # Check cache first
        if not force_refresh and self._is_cache_valid():
            logger.debug('Using cached bot configuration')
            return self._config_cache
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/bot/config/current/',
                    headers=self._get_headers()
                )
            
            if response.status_code == 200:
                config = response.json()
                
                # Cache the config
                import time
                self._config_cache = config
                self._cache_time = time.time()
                
                logger.info(f'✅ Bot config fetched from Spaxce: {config.get("hotel_name")}')
                return config
            
            elif response.status_code == 404:
                logger.warning('⚠️ No bot configuration found in Spaxce')
                return None
            
            else:
                logger.error(f'❌ API error {response.status_code}: {response.text}')
                return self._config_cache  # Return cached config as fallback
        
        except Exception as e:
            logger.error(f'❌ Failed to fetch bot config: {e}')
            return self._config_cache  # Return cached config as fallback
    
    async def get_bot_config_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Lookup bot configuration by WhatsApp phone number.
        
        Args:
            phone: WhatsApp phone number
        
        Returns:
            Bot configuration dict or None if not found
        """
        try:
            # Strip + for URL if present (will be re-added by API)
            clean_phone = phone.lstrip('+')
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/bot/config/by-phone/{clean_phone}/',
                    headers=self._get_headers()
                )
            
            if response.status_code == 200:
                config = response.json()
                logger.info(f'✅ Found bot config for phone {phone}: {config.get("hotel_name")}')
                return config
            else:
                logger.warning(f'⚠️ No bot configuration found for phone {phone}')
                return None
        except Exception as e:
            logger.error(f'❌ Error looking up bot config by phone: {e}')
            return None
    
    async def get_whatsapp_token(self) -> str:
        """Get WhatsApp API token from Spaxce."""
        config = await self.get_bot_config()
        return config.get('meta_access_token', '') if config else ''
    
    async def get_verify_token(self) -> str:
        """Get webhook verification token from Spaxce."""
        config = await self.get_bot_config()
        return config.get('webhook_verify_token', '') if config else ''
    
    async def get_gemini_api_key(self) -> str:
        """Get Gemini API key from Spaxce."""
        config = await self.get_bot_config()
        return config.get('gemini_api_key', '') if config else ''
    
    async def get_phone_number_id(self) -> str:
        """Get WhatsApp phone number ID from Spaxce."""
        config = await self.get_bot_config()
        return config.get('whatsapp_phone_number_id', '') if config else ''
    
    async def get_hotel_info(self) -> Dict[str, str]:
        """Get hotel information from Spaxce."""
        config = await self.get_bot_config()
        if not config:
            return {}
        
        return {
            'name': config.get('hotel_name', 'Hotel'),
            'email': config.get('hotel_email', ''),
            'phone': config.get('hotel_phone', ''),
            'address': config.get('hotel_address', '')
        }
    
    async def is_bot_enabled(self) -> bool:
        """Check if bot is enabled in Spaxce."""
        config = await self.get_bot_config()
        return config.get('is_enabled', False) if config else False
    
    async def get_hotel_rooms(self, hotel_id: int, available_only: bool = False) -> List[Dict]:
        """
        Get hotel rooms from Spaxce API.
        
        Args:
            hotel_id: Hotel ID
            available_only: Only return available rooms
        
        Returns:
            List of room dicts
        """
        try:
            params = {}
            if available_only:
                params['available'] = 'true'
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/hotel/{hotel_id}/rooms/',
                    headers=self._get_headers(),
                    params=params
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f'❌ Failed to fetch rooms: {response.status_code}')
                return []
        
        except Exception as e:
            logger.error(f'❌ Error fetching hotel rooms: {e}')
            return []
    
    async def get_room_types(self, hotel_id: int) -> List[Dict]:
        """Get room types from Spaxce API."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/hotel/{hotel_id}/room-types/',
                    headers=self._get_headers()
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f'❌ Failed to fetch room types: {response.status_code}')
                return []
        
        except Exception as e:
            logger.error(f'❌ Error fetching room types: {e}')
            return []
    
    async def get_availability(self, hotel_id: int) -> Optional[Dict]:
        """Get hotel availability summary from Spaxce API."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/hotel/{hotel_id}/availability/',
                    headers=self._get_headers()
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f'❌ Failed to fetch availability: {response.status_code}')
                return None
        
        except Exception as e:
            logger.error(f'❌ Error fetching availability: {e}')
            return None
    
    async def log_conversation(
        self,
        phone: str,
        message: str,
        response: str,
        conversation_type: str = 'inquiry',
        sentiment: str = 'neutral'
    ) -> bool:
        """
        Log conversation to Spaxce for analytics.
        
        Args:
            phone: Guest phone number
            message: Guest message
            response: Bot response
            conversation_type: Type of conversation (inquiry, booking, support)
            sentiment: Message sentiment (positive, neutral, negative)
        
        Returns:
            True if logged successfully
        """
        try:
            payload = {
                'phone': phone,
                'message': message,
                'response': response,
                'conversation_type': conversation_type,
                'sentiment': sentiment
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f'{self.base_url}/api/v1/conversations/log/',
                    headers=self._get_headers(),
                    json=payload
                )
            
            return response.status_code == 201
        
        except Exception as e:
            logger.error(f'❌ Error logging conversation: {e}')
            return False
    
    async def log_escalation(
        self,
        phone: str,
        reason: str,
        assigned_to: Optional[str] = None
    ) -> bool:
        """
        Log escalation to Spaxce.
        
        Args:
            phone: Guest phone number
            reason: Escalation reason
            assigned_to: Staff member ID to assign to
        
        Returns:
            True if logged successfully
        """
        try:
            payload = {
                'phone': phone,
                'reason': reason,
                'assigned_to': assigned_to
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f'{self.base_url}/api/v1/escalations/log/',
                    headers=self._get_headers(),
                    json=payload
                )
            
            return response.status_code == 201
        
        except Exception as e:
            logger.error(f'❌ Error logging escalation: {e}')
            return False
            
    async def get_bot_session(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Get bot session state for a guest phone number.
        
        Args:
            phone: Guest phone number
            
        Returns:
            Session data dict or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/bot/session/{phone}/',
                    headers=self._get_headers()
                )
            
            if response.status_code == 200:
                data = response.json()
                # state_data is a string (JSON-formatted), need to parse it
                import json
                try:
                    return json.loads(data.get('state_data', '{}'))
                except json.JSONDecodeError:
                    return {}
            elif response.status_code == 404:
                return None
            else:
                logger.error(f'❌ Failed to fetch session for {phone}: {response.status_code}')
                return None
        except Exception as e:
            logger.error(f'❌ Error fetching session: {e}')
            return None
            
    async def save_bot_session(self, phone: str, state: Dict[str, Any]) -> bool:
        """
        Save bot session state for a guest phone number.
        
        Args:
            phone: Guest phone number
            state: State dictionary to save
            
        Returns:
            True if saved successfully
        """
        try:
            import json
            payload = {
                'guest_phone': phone,
                'state_data': json.dumps(state)
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f'{self.base_url}/api/v1/bot/session/save/',
                    headers=self._get_headers(),
                    json=payload
                )
                
            return response.status_code == 200
        except Exception as e:
            logger.error(f'❌ Error saving session for {phone}: {e}')
            return False
            
    async def initialize_payment(self, booking_id: int, amount: Optional[float] = None, email: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Initialize payment via Spaxce API.
        
        Args:
            booking_id: Booking ID
            amount: Optional amount
            email: Optional email
            
        Returns:
            Dict containing authorization_url or None
        """
        try:
            payload = {
                'booking_id': booking_id,
                'amount': amount,
                'email': email
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f'{self.base_url}/api/v1/booking/payment/initialize/',
                    headers=self._get_headers(),
                    json=payload
                )
                
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f'❌ Failed to initialize payment for booking {booking_id}: {response.text}')
                return None
        except Exception as e:
            logger.error(f'❌ Error initializing payment: {e}')
            return None

    # ========== BOOKING API METHODS ==========
    
    async def get_room_types_list(self) -> List[Dict]:
        """
        Get list of room types with pricing and details.
        
        Returns:
            List of room type dicts with pricing info
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/booking/room-types/',
                    headers=self._get_headers()
                )
            
            if response.status_code == 200:
                logger.info('✅ Room types fetched successfully')
                return response.json()
            else:
                logger.error(f'❌ Failed to fetch room types: {response.status_code}')
                return []
        
        except Exception as e:
            logger.error(f'❌ Error fetching room types: {e}')
            return []
    
    async def check_availability(
        self,
        room_type_id: int,
        check_in: str,
        check_out: str
    ) -> Optional[Dict]:
        """
        Check room availability for given dates with instant pricing.
        
        Args:
            room_type_id: Room type ID
            check_in: Check-in date (DD/MM/YYYY or ISO format)
            check_out: Check-out date (DD/MM/YYYY or ISO format)
        
        Returns:
            Dict with availability, available count, and pricing info
        """
        try:
            params = {
                'room_type_id': room_type_id,
                'check_in': check_in,
                'check_out': check_out
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/booking/availability/',
                    headers=self._get_headers(),
                    params=params
                )
            
            if response.status_code == 200:
                logger.info(f'✅ Availability checked for room {room_type_id}')
                return response.json()
            else:
                logger.error(f'❌ Failed to check availability: {response.status_code}')
                return None
        
        except Exception as e:
            logger.error(f'❌ Error checking availability: {e}')
            return None
    
    async def create_booking(self, booking_data: Dict) -> Optional[Dict]:
        """
        Create a new booking.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f'{self.base_url}/api/v1/booking/create/',
                    headers=self._get_headers(),
                    json=booking_data
                )
            
            if response.status_code == 201:
                booking = response.json()
                logger.info(f'✅ Booking created: {booking.get("id")}')
                return booking
            else:
                logger.error(f'❌ Failed to create booking: {response.status_code} - {response.text}')
                return None
        except Exception as e:
            logger.error(f'❌ Error creating booking: {e}')
            return None
    
    async def lookup_booking(self, reference: str) -> Optional[Dict]:
        """
        Lookup booking by reference number via API.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/booking/lookup/{reference}/',
                    headers=self._get_headers()
                )
            
            if response.status_code == 200:
                logger.info(f'✅ Booking {reference} found via API')
                return response.json()
            else:
                logger.warning(f'⚠️ Booking {reference} not found: {response.status_code}')
                return None
        except Exception as e:
            logger.error(f'❌ Error looking up booking {reference}: {e}')
            return None
    
    async def get_booking(self, booking_id: int) -> Optional[Dict]:
        """
        Get booking details.
        
        Args:
            booking_id: Booking ID
        
        Returns:
            Booking dict with full details
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/booking/{booking_id}/',
                    headers=self._get_headers()
                )
            
            if response.status_code == 200:
                logger.info(f'✅ Booking {booking_id} retrieved')
                return response.json()
            else:
                logger.error(f'❌ Failed to get booking: {response.status_code}')
                return None
        
        except Exception as e:
            logger.error(f'❌ Error getting booking: {e}')
            return None
    
    async def update_booking_status(self, booking_id: int, status: str) -> Optional[Dict]:
        """
        Update booking status.
        
        Args:
            booking_id: Booking ID
            status: New status (PENDING, CONFIRMED, CHECKED_IN, CANCELLED)
        
        Returns:
            Updated booking dict
        """
        try:
            payload = {'status': status}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f'{self.base_url}/api/v1/booking/{booking_id}/status/',
                    headers=self._get_headers(),
                    json=payload
                )
            
            if response.status_code == 200:
                logger.info(f'✅ Booking {booking_id} status updated to {status}')
                return response.json()
            else:
                logger.error(f'❌ Failed to update booking status: {response.status_code}')
                return None
        
        except Exception as e:
            logger.error(f'❌ Error updating booking status: {e}')
            return None
    
    async def get_menu(self, category: Optional[str] = None) -> List[Dict]:
        """
        Get menu items (food and beverages).
        
        Args:
            category: Optional category filter (FOOD, DRINK, etc.)
        
        Returns:
            List of menu items with prices
        """
        try:
            params = {}
            if category:
                params['category'] = category
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/menu/',
                    headers=self._get_headers(),
                    params=params
                )
            
            if response.status_code == 200:
                logger.info('✅ Menu items fetched')
                return response.json()
            else:
                logger.error(f'❌ Failed to fetch menu: {response.status_code}')
                return []
        
        except Exception as e:
            logger.error(f'❌ Error fetching menu: {e}')
            return []
    
    async def create_order(self, order_data: Dict) -> Optional[Dict]:
        """
        Create a room service order.
        
        Args:
            order_data: Dict with:
                - booking_id: int
                - items: list of {'menu_item_id': int, 'quantity': int}
                - delivery_time: str (HH:MM, optional)
                - special_instructions: str (optional)
        
        Returns:
            Created order dict with order_id
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f'{self.base_url}/api/v1/order/create/',
                    headers=self._get_headers(),
                    json=order_data
                )
            
            if response.status_code == 201:
                order = response.json()
                logger.info(f'✅ Order created: {order.get("id")}')
                return order
            else:
                logger.error(f'❌ Failed to create order: {response.status_code} - {response.text}')
                return None
        
        except Exception as e:
            logger.error(f'❌ Error creating order: {e}')
            return None
    
    async def get_order(self, order_id: int) -> Optional[Dict]:
        """
        Get order details.
        
        Args:
            order_id: Order ID
        
        Returns:
            Order dict with status and items
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f'{self.base_url}/api/v1/order/{order_id}/',
                    headers=self._get_headers()
                )
            
            if response.status_code == 200:
                logger.info(f'✅ Order {order_id} retrieved')
                return response.json()
            else:
                logger.error(f'❌ Failed to get order: {response.status_code}')
                return None
        
        except Exception as e:
            logger.error(f'❌ Error getting order: {e}')
            return None


# Global instance
_api_client = None


def get_api_client() -> SpaxceAPIClient:
    """Get or create global API client instance."""
    global _api_client
    if _api_client is None:
        _api_client = SpaxceAPIClient()
    return _api_client


# Convenience async functions
async def get_bot_config() -> Optional[Dict[str, Any]]:
    """Get bot configuration from Spaxce."""
    return await get_api_client().get_bot_config()


async def get_whatsapp_token() -> str:
    """Get WhatsApp token from Spaxce."""
    return await get_api_client().get_whatsapp_token()


async def get_verify_token() -> str:
    """Get verification token from Spaxce."""
    return await get_api_client().get_verify_token()


async def get_gemini_api_key() -> str:
    """Get Gemini API key from Spaxce."""
    return await get_api_client().get_gemini_api_key()


async def get_hotel_info() -> Dict[str, str]:
    """Get hotel info from Spaxce."""
    return await get_api_client().get_hotel_info()


async def is_bot_enabled() -> bool:
    """Check if bot is enabled in Spaxce."""
    return await get_api_client().is_bot_enabled()


# ========== BOOKING API CONVENIENCE FUNCTIONS ==========

async def get_room_types_list() -> List[Dict]:
    """Get list of room types from Spaxce."""
    return await get_api_client().get_room_types_list()


async def check_availability(
    room_type_id: int,
    check_in: str,
    check_out: str
) -> Optional[Dict]:
    """Check room availability with pricing."""
    return await get_api_client().check_availability(room_type_id, check_in, check_out)


async def create_booking(booking_data: Dict) -> Optional[Dict]:
    """Create a new booking."""
    return await get_api_client().create_booking(booking_data)


async def get_booking(booking_id: int) -> Optional[Dict]:
    """Get booking details by ID."""
    return await get_api_client().get_booking(booking_id)


async def lookup_booking(reference: str) -> Optional[Dict]:
    """Lookup booking by reference number."""
    return await get_api_client().lookup_booking(reference)


async def update_booking_status(booking_id: int, status: str) -> Optional[Dict]:
    """Update booking status."""
    return await get_api_client().update_booking_status(booking_id, status)


async def get_menu(category: Optional[str] = None) -> List[Dict]:
    """Get menu items."""
    return await get_api_client().get_menu(category)


async def create_order(order_data: Dict) -> Optional[Dict]:
    """Create a room service order."""
    return await get_api_client().create_order(order_data)


async def get_order(order_id: int) -> Optional[Dict]:
    """Get order details."""
    return await get_api_client().get_order(order_id)


async def get_bot_config_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """Lookup bot configuration by WhatsApp phone number."""
    return await get_api_client().get_bot_config_by_phone(phone)


async def get_bot_session(phone: str) -> Optional[Dict[str, Any]]:
    """Get bot session state."""
    return await get_api_client().get_bot_session(phone)


async def save_bot_session(phone: str, state: Dict[str, Any]) -> bool:
    """Save bot session state."""
    return await get_api_client().save_bot_session(phone, state)


async def initialize_payment(booking_id: int, amount: Optional[float] = None, email: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Initialize payment."""
    return await get_api_client().initialize_payment(booking_id, amount, email)
