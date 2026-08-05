# -*- coding: utf-8 -*-
"""
Hotel WhatsApp Bot — FastAPI Entry Point

Main application file that sets up FastAPI routes for WhatsApp webhooks,
health checks, and API-driven guest communication.

UPDATED: Refactored to be API-only. No direct database dependencies.
"""

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables at startup
load_dotenv()

app = FastAPI(
    title="Hotel WhatsApp Bot (API-Only)",
    version="2.0.0",
    docs_url="/api/docs"
)


@app.on_event("startup")
async def startup():
    """Application startup logic."""
    logger.info("🚀 Starting Hotel WhatsApp Bot in API-Only mode...")
    # Verify environment
    if not os.getenv("SPAXCE_API_TOKEN"):
        logger.error("❌ SPAXCE_API_TOKEN not configured!")
    if not os.getenv("SPAXCE_API_URL"):
        logger.error("❌ SPAXCE_API_URL not configured!")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "hotel-whatsapp-bot",
        "mode": "api-only",
        "version": "2.0.0"
    }


@app.get("/webhook")
async def verify_webhook_endpoint(request: Request):
    """
    Verify webhook with Meta Cloud API.
    """
    try:
        query_params = request.query_params
        
        hub_mode = query_params.get("hub.mode") or query_params.get("hub_mode")
        hub_challenge = query_params.get("hub.challenge") or query_params.get("hub_challenge")
        hub_verify_token = query_params.get("hub.verify_token") or query_params.get("hub_verify_token")
        
        from src.webhook import verify_webhook
        return await verify_webhook(hub_mode, hub_challenge, hub_verify_token)
        
    except Exception as e:
        logger.error(f"Webhook verification error: {e}")
        return JSONResponse(
            {"error": f"Verification failed: {str(e)}"},
            status_code=500
        )


@app.post("/webhook")
async def receive(request: Request, background_tasks: BackgroundTasks):
    """Receive incoming messages from Meta WhatsApp Cloud API."""
    from src.webhook import handle_incoming
    try:
        body = await request.json()
        background_tasks.add_task(handle_incoming, body)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error receiving webhook: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)


@app.post("/api/v1/notify/payment")
async def payment_notification(request: Request):
    """
    Endpoint for Spaxce Backend to notify the bot about successful payments.
    This replaces the direct Paystack webhook.
    """
    try:
        data = await request.json()
        phone = data.get("phone")
        message = data.get("message")
        
        if not phone or not message:
            return JSONResponse({"error": "Missing phone or message"}, status_code=400)
            
        from src.messenger import send_text
        await send_text(phone, message)
        
        logger.info(f"✅ Payment notification sent to {phone}")
        return {"status": "sent"}
    except Exception as e:
        logger.error(f"Error in payment notification: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
