"""
LABBAIK.AI WhatsApp Bot - Main Application
==========================================
FastAPI webhook receiver for WAHA (WhatsApp HTTP API)
Integrates with Groq AI for intelligent Umrah planning assistance
"""

import os
import logging
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import httpx
from datetime import datetime

from config.settings import settings
from handlers.message_handler import MessageHandler
from services.waha_service import WAHAService
from services.ai_service import AIService
from services.database_service import DatabaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
waha_service = WAHAService()
ai_service = AIService()
db_service = DatabaseService()
message_handler = MessageHandler(waha_service, ai_service, db_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("🚀 Starting LABBAIK WhatsApp Bot...")
    logger.info(f"📱 WAHA URL: {settings.WAHA_API_URL}")
    logger.info(f"🤖 AI Model: {settings.GROQ_MODEL}")
    
    # Initialize database connection
    await db_service.initialize()
    
    # Verify WAHA connection
    if await waha_service.health_check():
        logger.info("✅ WAHA connection successful")
    else:
        logger.warning("⚠️ WAHA connection failed - bot may not work properly")
    
    yield
    
    # Cleanup
    await db_service.close()
    logger.info("👋 LABBAIK WhatsApp Bot shutting down...")


app = FastAPI(
    title="LABBAIK.AI WhatsApp Bot",
    description="AI-powered Umrah planning assistant via WhatsApp",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "LABBAIK.AI WhatsApp Bot",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    waha_status = await waha_service.health_check()
    
    return {
        "status": "healthy" if waha_status else "degraded",
        "components": {
            "waha": "connected" if waha_status else "disconnected",
            "ai": "ready",
            "database": "connected" if db_service.is_connected else "disconnected"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/webhook/waha")
async def waha_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Main webhook endpoint for WAHA
    Receives all WhatsApp events and processes messages
    """
    try:
        payload = await request.json()
        
        # Log incoming webhook
        event_type = payload.get("event", "unknown")
        logger.info(f"📨 Received webhook: {event_type}")
        
        # Handle different event types
        if event_type == "message":
            # Process message in background to respond quickly
            background_tasks.add_task(
                message_handler.handle_incoming_message,
                payload
            )
            return {"status": "accepted", "event": event_type}
        
        elif event_type == "message.ack":
            # Message acknowledgment (delivered, read, etc.)
            logger.debug(f"Message ACK: {payload.get('payload', {}).get('ack')}")
            return {"status": "acknowledged"}
        
        elif event_type == "session.status":
            # Session status update
            status = payload.get("payload", {}).get("status")
            logger.info(f"📱 Session status: {status}")
            return {"status": "noted"}
        
        else:
            logger.debug(f"Unhandled event type: {event_type}")
            return {"status": "ignored", "event": event_type}
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/test")
async def test_webhook(request: Request):
    """Test endpoint to simulate incoming messages"""
    try:
        payload = await request.json()
        phone = payload.get("phone", "6281234567890")
        message = payload.get("message", "Assalamualaikum")
        
        # Create simulated WAHA payload
        simulated_payload = {
            "event": "message",
            "payload": {
                "from": f"{phone}@c.us",
                "body": message,
                "timestamp": int(datetime.now().timestamp()),
                "fromMe": False,
                "hasMedia": False
            },
            "session": settings.WAHA_SESSION
        }
        
        # Process the message
        await message_handler.handle_incoming_message(simulated_payload)
        
        return {"status": "test_processed", "phone": phone, "message": message}
    
    except Exception as e:
        logger.error(f"Test webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/send-message")
async def send_message(request: Request):
    """API endpoint to send message directly"""
    try:
        payload = await request.json()
        phone = payload.get("phone")
        message = payload.get("message")
        
        if not phone or not message:
            raise HTTPException(status_code=400, detail="phone and message required")
        
        result = await waha_service.send_message(phone, message)
        return {"status": "sent", "result": result}
    
    except Exception as e:
        logger.error(f"Send message error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/broadcast")
async def broadcast_message(request: Request):
    """Broadcast message to multiple recipients"""
    try:
        payload = await request.json()
        phones = payload.get("phones", [])
        message = payload.get("message")
        
        if not phones or not message:
            raise HTTPException(status_code=400, detail="phones and message required")
        
        results = []
        for phone in phones:
            try:
                result = await waha_service.send_message(phone, message)
                results.append({"phone": phone, "status": "sent"})
            except Exception as e:
                results.append({"phone": phone, "status": "failed", "error": str(e)})
        
        return {"status": "completed", "results": results}
    
    except Exception as e:
        logger.error(f"Broadcast error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get bot statistics"""
    try:
        stats = await db_service.get_stats()
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
