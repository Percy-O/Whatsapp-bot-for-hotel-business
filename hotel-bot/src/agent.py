"""
Gemini AI Agent — Comprehensive Guest Support Handler (2026 Standard)

Handles ALL guest inquiries using Gemini 2.5 Flash AI.
Trained to understand complex requests, provide relevant information, and handle support comprehensively.

UPDATED: Now communicates EXCLUSIVELY via Spaxce API.
"""

import google.generativeai as genai
import json
import os
import logging
from src.spaxce_api_client import (
    get_gemini_api_key, get_hotel_info, get_api_client,
    get_bot_config, get_room_types_list, log_conversation
)

logger = logging.getLogger(__name__)

# Global model instance
_model_cache = {}


def build_system_prompt(hotel_info: dict, rooms: list, faq: dict) -> str:
    """
    Build comprehensive system prompt for Gemini (2026 Standard - Maximum Responsiveness).
    """
    
    # Build room details string
    room_details = "\n".join([
        f"- {room.get('name', 'Room')}: ₦{float(room.get('price_per_night', 0)):,}/night (Capacity: {room.get('capacity', 1)} guests)\n"
        f"  Amenities: {', '.join(room.get('amenities', [])) if isinstance(room.get('amenities'), list) else room.get('amenities', '')}"
        for room in rooms
    ])
    
    # Build FAQ section
    faq_section = "\n".join([
        f"- {key.upper().replace('_', ' ')}: {value}"
        for key, value in faq.items()
    ])
    
    hotel_name = hotel_info.get('name', 'Our Hotel')
    location = hotel_info.get('address', 'Nigeria')
    
    prompt = f"""You are an INTELLIGENT, RESPONSIVE, and COMPREHENSIVE booking assistant for {hotel_name}, located in {location}.

===== YOUR PRIMARY MISSION =====
✅ Handle VIRTUALLY ALL guest messages about {hotel_name}
✅ Provide relevant, adequate, confident responses
✅ Make guests feel heard, valued, and confident about their stay
✅ NEVER say "I don't know" - always offer a solution
✅ Only escalate on genuine pressing needs (emergencies, serious complaints, explicit requests)

===== CRITICAL PRINCIPLES =====
1. **Be Responsive**: Answer questions directly, confidently, and helpfully
2. **Be Adequate**: Provide complete information that satisfies the guest
3. **Be Proactive**: Anticipate needs and offer suggestions
4. **Be Professional**: Use warm, confident, conversational tone
5. **Be Helpful**: Frame everything in terms of what you CAN do, not what you can't

===== MAXIMUM RESPONSIVENESS TRAINING =====
You should handle:
1. **All hotel information questions** - Room details, pricing, amenities, policies
2. **Booking decisions** - Help guests choose the right room for them
3. **Complex requests** - Multi-part questions, special needs, group bookings
4. **Travel planning** - What to pack, things to do, local info
5. **Reassurance & support** - Nervous guests, families with kids, accessibility needs
6. **General hospitality** - Welcome messages, check-in info, house rules

===== HOTEL FACTS (USE ONLY THESE FOR PRICING/POLICIES) =====

**Location & Contact:**
- Address: {hotel_info.get('address', 'Location not available')}
- Email: {hotel_info.get('email', 'Email not available')}
- Phone: {hotel_info.get('phone', 'Phone not available')}

**Room Types & Prices:**
{room_details if room_details else 'Room information is being loaded. Please ask about our available rooms.'}

**Frequently Asked Questions & EXACT Answers:**
{faq_section if faq_section else 'Please ask about our policies and amenities.'}

===== YOUR MINDSET =====
- Every message deserves a HELPFUL, ADEQUATE response
- You are capable of handling virtually all guest needs
- Your goal is to make guests feel confident, welcome, and excited to stay
"""
    return prompt


def get_gemini_model(api_key: str):
    """Get or initialize Gemini model."""
    if api_key in _model_cache:
        return _model_cache[api_key]
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        _model_cache[api_key] = model
        logger.info("✓ Gemini model initialized")
        return model
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini model: {e}")
        raise


async def ask(phone: str, message: str, session: dict, hotel_id: int) -> None:
    """
    Handle guest inquiries using Gemini 2.5 Flash AI via Spaxce API.
    """
    from src.session import append_history, save_session
    from src.messenger import send_text, log_outbound
    
    try:
        logger.info(f"🤖 AI processing message from {phone}: {message[:50]}... (Hotel ID: {hotel_id})")
        
        # === STEP 1: Fetch hotel configuration and data via API ===
        bot_config = await get_bot_config() # Fetches current enabled config
        if not bot_config:
            logger.error(f"❌ No active bot config found via API")
            from src.handlers.escalate import start as escalate_start
            await escalate_start(phone, "System configuration error - no bot setup found")
            return
        
        # Get Gemini API key
        gemini_api_key = bot_config.get('gemini_api_key')
        if not gemini_api_key:
            gemini_api_key = await get_gemini_api_key()
            
        if not gemini_api_key:
            logger.error(f"❌ No Gemini API key configured")
            from src.handlers.escalate import start as escalate_start
            await escalate_start(phone, "System error - AI service not configured")
            return
        
        # Initialize Gemini model
        model = get_gemini_model(gemini_api_key)
        
        # Fetch hotel data from Spaxce API
        hotel_info = await get_hotel_info()
        rooms = await get_room_types_list()
        
        # Parse FAQ from knowledge base
        faq = {}
        kb = bot_config.get('knowledge_base')
        if kb:
            try:
                faq = json.loads(kb) if isinstance(kb, str) else kb
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"⚠️ Failed to parse knowledge_base JSON: {e}")
        
        # Fallback FAQs if empty
        if not faq:
            faq = {
                "check_in": "14:00 (2:00 PM)",
                "check_out": "11:00 (11:00 AM)",
                "cancellation": "24 hours notice required",
                "wifi": "Complimentary high-speed WiFi available in all rooms"
            }
        
        # === STEP 2: Build system prompt ===
        system_prompt = build_system_prompt(hotel_info, rooms, faq)
        
        # Append user message to history
        session = append_history(session, "user", message)
        
        # === STEP 3: Build complete prompt ===
        prompt_parts = [system_prompt, "\n\n=== CONVERSATION HISTORY ==="]
        for msg in session.get("history", []):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"{'Guest' if role == 'user' else 'Assistant'}: {content}")
        
        prompt_parts.append("\n=== END CONVERSATION HISTORY ===")
        prompt_parts.append(f"\nRespond helpfully: {message}")
        
        full_prompt = "\n".join(prompt_parts)
        
        # === STEP 4: Generate response ===
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=400,
                temperature=0.5
            )
        )
        
        reply = response.text.strip()
        
        # === STEP 5: Validate response ===
        unhelpful_patterns = ["i don't have information", "i cannot help", "outside my scope"]
        if any(pattern in reply.lower() for pattern in unhelpful_patterns):
            from src.handlers.escalate import start as escalate_start
            await escalate_start(phone, f"AI couldn't help with: {message}")
            return
        
        # === STEP 6: Save to history and log via API ===
        session = append_history(session, "assistant", reply)
        await save_session(phone, session)
        
        # Log via API
        await log_conversation(
            phone=phone,
            message=message,
            response=reply,
            conversation_type="inquiry"
        )
        
        # === STEP 7: Send reply ===
        success = await send_text(phone, reply)
        if success:
            await log_outbound(phone, reply, "gemini_agent")
        
    except Exception as e:
        logger.error(f"❌ Gemini AI error for {phone}: {e}", exc_info=True)
        from src.handlers.escalate import start as escalate_start
        await escalate_start(phone, f"AI Error: {type(e).__name__}")
