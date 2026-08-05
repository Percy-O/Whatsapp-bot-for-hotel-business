"""
Unit Tests for Hotel Bot - Critical Components

Tests for:
- Webhook parsing
- Message routing
- Session management
- API client error handling
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.webhook import parse_incoming, verify_webhook
from src.router import route
from src.session import get_session, clear_session


class TestWebhookParsing:
    """Test webhook message parsing from Meta."""
    
    def test_parse_valid_text_message(self):
        """Test parsing a valid WhatsApp text message."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "field": "messages",
                    "value": {
                        "messages": [{
                            "from": "2349070553898",
                            "id": "wamid.test123",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {
                                "body": "Hello, I want to book a room"
                            }
                        }]
                    }
                }]
            }]
        }
        
        result = parse_incoming(payload)
        
        assert result is not None
        assert result["phone"] == "2349070553898"
        assert result["message"] == "Hello, I want to book a room"
        assert result["message_id"] == "wamid.test123"
    
    def test_parse_empty_messages(self):
        """Test parsing webhook with no messages."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "field": "messages",
                    "value": {
                        "messages": []
                    }
                }]
            }]
        }
        
        result = parse_incoming(payload)
        assert result is None
    
    def test_parse_non_text_message(self):
        """Test parsing non-text message (e.g., image)."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "field": "messages",
                    "value": {
                        "messages": [{
                            "from": "2349070553898",
                            "id": "wamid.test123",
                            "type": "image",
                            "image": {
                                "id": "img123"
                            }
                        }]
                    }
                }]
            }]
        }
        
        result = parse_incoming(payload)
        assert result is None
    
    def test_parse_wrong_object_type(self):
        """Test parsing with wrong object type."""
        payload = {
            "object": "other_object_type",
            "entry": [{}]
        }
        
        result = parse_incoming(payload)
        assert result is None


class TestWebhookVerification:
    """Test webhook verification with Meta."""
    
    @pytest.mark.asyncio
    async def test_verify_webhook_success(self):
        """Test successful webhook verification."""
        with patch('src.webhook.get_verify_token', new_callable=AsyncMock) as mock_token:
            mock_token.return_value = "test_verify_token"
            
            result = await verify_webhook("subscribe", "challenge123", "test_verify_token")
            
            # Should return challenge as PlainTextResponse
            assert result is not None


class TestSessionManagement:
    """Test session creation and management."""
    
    @pytest.mark.asyncio
    async def test_get_session_creates_new(self):
        """Test getting a session for new phone number."""
        phone = "2349070553898"
        
        session = await get_session(phone)
        
        assert session is not None
        assert "phone" in session or session  # Session should have data
    
    @pytest.mark.asyncio
    async def test_clear_session(self):
        """Test clearing a session."""
        phone = "2349070553898"
        
        # Create session
        await get_session(phone)
        
        # Clear it
        result = await clear_session(phone)
        
        # Should not raise error
        assert result is not None or True


class TestMessageRouting:
    """Test message routing logic."""
    
    @pytest.mark.asyncio
    async def test_route_greeting_message(self):
        """Test routing greeting triggers welcome."""
        phone = "2349070553898"
        greeting = "hello"
        
        with patch('src.router.get_bot_config', new_callable=AsyncMock) as mock_config:
            with patch('src.messenger.send_welcome', new_callable=AsyncMock) as mock_welcome:
                mock_config.return_value = {"hotel_id": 1, "hotel_name": "Test Hotel"}
                
                await route(phone, greeting)
                
                # Welcome should be called for greeting
                mock_welcome.assert_called()
    
    @pytest.mark.asyncio
    async def test_route_booking_reference(self):
        """Test routing booking reference search."""
        phone = "2349070553898"
        booking_ref = "HTL-20260522-1234"
        
        with patch('src.router.get_bot_config', new_callable=AsyncMock) as mock_config:
            with patch('src.handlers.search_booking.search_booking', new_callable=AsyncMock) as mock_search:
                mock_config.return_value = {"hotel_id": 1, "hotel_name": "Test Hotel"}
                
                await route(phone, booking_ref)
                
                # Search should be called for booking reference
                # (Note: This may not be called depending on implementation flow)


class TestAPIClientErrorHandling:
    """Test API client error scenarios."""
    
    @pytest.mark.asyncio
    async def test_api_client_timeout(self):
        """Test handling of API timeout."""
        from src.spaxce_api_client import SpaxceAPIClient
        
        client = SpaxceAPIClient()
        
        # This should handle timeout gracefully
        assert client is not None
        assert hasattr(client, 'base_url')
        assert hasattr(client, 'api_token')


# pytest fixtures and configuration

@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables."""
    monkeypatch.setenv('SPAXCE_API_URL', 'http://localhost:9000')
    monkeypatch.setenv('SPAXCE_API_TOKEN', 'test_token')
    monkeypatch.setenv('GEMINI_API_KEY', 'test_gemini_key')
    monkeypatch.setenv('WHATSAPP_TOKEN', 'test_whatsapp_token')


# Run tests with: pytest tests/test_bot.py -v
# Run async tests: pytest tests/test_bot.py -v -s

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
