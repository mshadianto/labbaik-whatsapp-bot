"""
LABBAIK.AI WhatsApp Bot - WAHA Service
======================================
Service for interacting with WAHA (WhatsApp HTTP API)
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from config.settings import settings

logger = logging.getLogger(__name__)


class WAHAService:
    """Service for WAHA API interactions"""
    
    def __init__(self):
        self.base_url = settings.WAHA_API_URL.rstrip('/')
        self.session = settings.WAHA_SESSION
        self.headers = {
            "Content-Type": "application/json"
        }
        if settings.WAHA_API_KEY:
            self.headers["X-Api-Key"] = settings.WAHA_API_KEY
    
    async def health_check(self) -> bool:
        """Check WAHA connection and session status"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/sessions/{self.session}",
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status", "UNKNOWN")
                    logger.info(f"WAHA session status: {status}")
                    return status == "WORKING"
                return False
        except Exception as e:
            logger.error(f"WAHA health check error: {e}")
            return False
    
    async def send_message(
        self, 
        chat_id: str, 
        message: str,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a text message to a WhatsApp chat
        
        Args:
            chat_id: Chat ID with suffix (e.g., "628xxx@c.us" or "123xxx@lid")
            message: Text message to send
            reply_to: Optional message ID to reply to
        """
        # Ensure chat_id has proper format
        if "@" not in chat_id:
            # If no suffix, assume @c.us for phone numbers
            chat_id = f"{self._clean_phone(chat_id)}@c.us"
        
        payload = {
            "chatId": chat_id,
            "text": message,
            "session": self.session
        }
        
        if reply_to:
            payload["reply_to"] = reply_to
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sendText",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200 or response.status_code == 201:
                    logger.info(f"✅ Message sent to {chat_id}")
                    return response.json()
                else:
                    logger.error(f"❌ Failed to send message: {response.status_code} - {response.text}")
                    raise Exception(f"Send failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"❌ Send message error: {e}")
            raise
    
    async def send_image(
        self,
        chat_id: str,
        image_url: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send an image message"""
        if "@" not in chat_id:
            chat_id = f"{self._clean_phone(chat_id)}@c.us"
        
        payload = {
            "chatId": chat_id,
            "file": {
                "url": image_url
            },
            "session": self.session
        }
        
        if caption:
            payload["caption"] = caption
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sendImage",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ Image sent to {chat_id}")
                    return response.json()
                else:
                    raise Exception(f"Send image failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"❌ Send image error: {e}")
            raise
    
    async def send_document(
        self,
        chat_id: str,
        document_url: str,
        filename: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a document/file"""
        if "@" not in chat_id:
            chat_id = f"{self._clean_phone(chat_id)}@c.us"
        
        payload = {
            "chatId": chat_id,
            "file": {
                "url": document_url,
                "filename": filename
            },
            "session": self.session
        }
        
        if caption:
            payload["caption"] = caption
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sendFile",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ Document sent to {chat_id}")
                    return response.json()
                else:
                    raise Exception(f"Send document failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"❌ Send document error: {e}")
            raise
    
    async def send_buttons(
        self,
        chat_id: str,
        message: str,
        buttons: List[Dict[str, str]],
        footer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message with buttons (if supported by WAHA version)
        
        Args:
            chat_id: Chat ID
            message: Main message text
            buttons: List of {"id": "btn_1", "text": "Button Text"}
            footer: Optional footer text
        """
        if "@" not in chat_id:
            chat_id = f"{self._clean_phone(chat_id)}@c.us"
        
        payload = {
            "chatId": chat_id,
            "text": message,
            "buttons": buttons,
            "session": self.session
        }
        
        if footer:
            payload["footer"] = footer
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sendButtons",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    # Fallback to regular text if buttons not supported
                    logger.warning("Buttons not supported, falling back to text")
                    button_text = "\n".join([f"• {b['text']}" for b in buttons])
                    return await self.send_message(chat_id, f"{message}\n\n{button_text}")
        
        except Exception as e:
            logger.error(f"❌ Send buttons error: {e}")
            # Fallback to text
            button_text = "\n".join([f"• {b['text']}" for b in buttons])
            return await self.send_message(chat_id, f"{message}\n\n{button_text}")
    
    async def send_list(
        self,
        chat_id: str,
        message: str,
        button_text: str,
        sections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send a list message (if supported)
        
        Args:
            chat_id: Chat ID
            message: Main message text
            button_text: Text for the list button
            sections: List of sections with rows
        """
        if "@" not in chat_id:
            chat_id = f"{self._clean_phone(chat_id)}@c.us"
        
        payload = {
            "chatId": chat_id,
            "text": message,
            "buttonText": button_text,
            "sections": sections,
            "session": self.session
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sendList",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    # Fallback to regular text
                    logger.warning("List not supported, falling back to text")
                    return await self.send_message(chat_id, message)
        
        except Exception as e:
            logger.error(f"❌ Send list error: {e}")
            return await self.send_message(chat_id, message)
    
    async def send_location(
        self,
        chat_id: str,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a location message"""
        if "@" not in chat_id:
            chat_id = f"{self._clean_phone(chat_id)}@c.us"
        
        payload = {
            "chatId": chat_id,
            "latitude": latitude,
            "longitude": longitude,
            "session": self.session
        }
        
        if name:
            payload["name"] = name
        if address:
            payload["address"] = address
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sendLocation",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    raise Exception(f"Send location failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"❌ Send location error: {e}")
            raise
    
    async def mark_as_read(self, chat_id: str) -> bool:
        """Mark messages in a chat as read"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sendSeen",
                    headers=self.headers,
                    json={
                        "chatId": chat_id,
                        "session": self.session
                    }
                )
                return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Mark as read error: {e}")
            return False
    
    async def start_typing(self, chat_id: str) -> bool:
        """Show typing indicator"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/startTyping",
                    headers=self.headers,
                    json={
                        "chatId": chat_id,
                        "session": self.session
                    }
                )
                return response.status_code in [200, 201]
        except Exception as e:
            logger.debug(f"Start typing error: {e}")
            return False
    
    async def stop_typing(self, chat_id: str) -> bool:
        """Stop typing indicator"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/stopTyping",
                    headers=self.headers,
                    json={
                        "chatId": chat_id,
                        "session": self.session
                    }
                )
                return response.status_code in [200, 201]
        except Exception as e:
            logger.debug(f"Stop typing error: {e}")
            return False
    
    async def get_contact_info(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get contact information"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/contacts",
                    headers=self.headers,
                    params={
                        "contactId": chat_id,
                        "session": self.session
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                return None
        
        except Exception as e:
            logger.error(f"Get contact error: {e}")
            return None
    
    def _clean_phone(self, phone: str) -> str:
        """Clean phone number, removing non-digits and @c.us suffix"""
        # Remove @c.us or @lid if present
        phone = phone.split("@")[0] if "@" in phone else phone
        # Remove non-digit characters except +
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        # Remove + if present
        phone = phone.replace("+", "")
        # Ensure Indonesian number format
        if phone.startswith("08"):
            phone = "62" + phone[1:]
        return phone
    
    def extract_phone_from_jid(self, jid: str) -> str:
        """Extract phone number from WhatsApp JID"""
        return jid.split("@")[0] if "@" in jid else jid
