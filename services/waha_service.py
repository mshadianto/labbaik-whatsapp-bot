"""
LABBAIK.AI WhatsApp Bot - WAHA Service (Enhanced v2)
=====================================================
Service for interacting with WAHA (WhatsApp HTTP API)
With support for buttons, lists, audio, images, locations, and documents
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from config.settings import settings

logger = logging.getLogger(__name__)


class WAHAService:
    """Enhanced service for WAHA API interactions"""
    
    def __init__(self):
        self.base_url = settings.WAHA_API_URL.rstrip('/')
        self.session = settings.WAHA_SESSION
        self.headers = {
            "Content-Type": "application/json"
        }
        if settings.WAHA_API_KEY:
            self.headers["X-Api-Key"] = settings.WAHA_API_KEY
    
    # ==================== HEALTH & STATUS ====================
    
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
    
    # ==================== BASIC MESSAGING ====================
    
    async def send_message(
        self, 
        chat_id: str, 
        message: str,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a text message
        
        Args:
            chat_id: Full chat ID (e.g., "628xxx@c.us" or "123xxx@lid")
            message: Text message to send
            reply_to: Optional message ID to reply to
        """
        if "@" not in chat_id:
            chat_id = f"{self._clean_phone(chat_id)}@c.us"
        
        payload = {
            "chatId": chat_id,
            "text": message,
            "session": self.session
        }
        
        if reply_to:
            payload["reply_to"] = reply_to
        
        return await self._post("/api/sendText", payload, "Message")
    
    # ==================== INTERACTIVE MESSAGES ====================
    
    async def send_buttons(
        self,
        chat_id: str,
        text: str,
        buttons: List[Dict[str, str]],
        footer: Optional[str] = None,
        header: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message with clickable buttons (max 3 buttons)
        
        Args:
            chat_id: Chat ID
            text: Main message text
            buttons: List of {"id": "btn_1", "text": "Button Text"}
            footer: Optional footer text
            header: Optional header text
            
        Example:
            buttons = [
                {"id": "menu_1", "text": "📖 Panduan Umrah"},
                {"id": "menu_2", "text": "🤲 Doa & Dzikir"},
                {"id": "menu_3", "text": "💰 Simulasi Biaya"}
            ]
        """
        if "@" not in chat_id:
            chat_id = f"{self._clean_phone(chat_id)}@c.us"
        
        # Format buttons for WAHA
        formatted_buttons = []
        for btn in buttons[:3]:  # Max 3 buttons
            formatted_buttons.append({
                "id": btn.get("id", f"btn_{len(formatted_buttons)}"),
                "text": btn.get("text", "Button")[:20]  # Max 20 chars
            })
        
        payload = {
            "chatId": chat_id,
            "text": text,
            "buttons": formatted_buttons,
            "session": self.session
        }
        
        if footer:
            payload["footer"] = footer[:60]  # Max 60 chars
        if header:
            payload["header"] = header
        
        try:
            result = await self._post("/api/sendButtons", payload, "Buttons")
            return result
        except Exception as e:
            # Fallback to regular text with emoji buttons
            logger.warning(f"Buttons not supported, falling back to text: {e}")
            fallback_text = text + "\n\n"
            for i, btn in enumerate(buttons, 1):
                fallback_text += f"*{i}.* {btn['text']}\n"
            if footer:
                fallback_text += f"\n_{footer}_"
            return await self.send_message(chat_id, fallback_text)
    
    async def send_list(
        self,
        chat_id: str,
        text: str,
        button_text: str,
        sections: List[Dict[str, Any]],
        footer: Optional[str] = None,
        header: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a list message with selectable items
        
        Args:
            chat_id: Chat ID
            text: Main message text
            button_text: Text on the list button (e.g., "Pilih Menu")
            sections: List of sections with rows
            footer: Optional footer text
            
        Example:
            sections = [
                {
                    "title": "Panduan",
                    "rows": [
                        {"id": "guide_ihram", "title": "Ihram", "description": "Tata cara ihram"},
                        {"id": "guide_tawaf", "title": "Tawaf", "description": "Tata cara tawaf"}
                    ]
                },
                {
                    "title": "Doa",
                    "rows": [
                        {"id": "doa_niat", "title": "Niat Umrah"},
                        {"id": "doa_talbiyah", "title": "Talbiyah"}
                    ]
                }
            ]
        """
        if "@" not in chat_id:
            chat_id = f"{self._clean_phone(chat_id)}@c.us"
        
        payload = {
            "chatId": chat_id,
            "text": text,
            "buttonText": button_text[:20],
            "sections": sections,
            "session": self.session
        }
        
        if footer:
            payload["footer"] = footer[:60]
        if header:
            payload["header"] = header
        
        try:
            result = await self._post("/api/sendList", payload, "List")
            return result
        except Exception as e:
            # Fallback to regular text
            logger.warning(f"List not supported, falling back to text: {e}")
            fallback_text = text + "\n\n"
            for section in sections:
                fallback_text += f"*{section.get('title', '')}*\n"
                for row in section.get('rows', []):
                    fallback_text += f"• {row.get('title', '')}\n"
                fallback_text += "\n"
            return await self.send_message(chat_id, fallback_text)
    
    async def send_quick_replies(
        self,
        chat_id: str,
        text: str,
        quick_replies: List[str]
    ) -> Dict[str, Any]:
        """
        Send message with quick reply suggestions
        Note: This uses buttons as quick replies
        
        Args:
            chat_id: Chat ID
            text: Main message text  
            quick_replies: List of quick reply texts (max 3)
            
        Example:
            quick_replies = ["Doa Ihram", "Larangan Ihram", "Menu"]
        """
        buttons = [
            {"id": f"qr_{i}", "text": qr[:20]} 
            for i, qr in enumerate(quick_replies[:3])
        ]
        
        return await self.send_buttons(
            chat_id=chat_id,
            text=text,
            buttons=buttons,
            footer="Ketuk untuk memilih"
        )
    
    # ==================== MEDIA MESSAGES ====================
    
    async def send_audio(
        self,
        chat_id: str,
        audio_url: str,
        caption: Optional[str] = None,
        as_voice: bool = True
    ) -> Dict[str, Any]:
        """
        Send audio message (voice note or audio file)
        
        Args:
            chat_id: Chat ID
            audio_url: URL to audio file (MP3, OGG, etc.)
            caption: Optional caption
            as_voice: If True, sends as voice message (PTT)
        """
        if "@" not in chat_id:
            chat_id = f"{self._clean_phone(chat_id)}@c.us"
        
        payload = {
            "chatId": chat_id,
            "file": {
                "url": audio_url
            },
            "session": self.session
        }
        
        if caption:
            payload["caption"] = caption
        
        # Use sendVoice for voice notes, sendFile for audio files
        endpoint = "/api/sendVoice" if as_voice else "/api/sendFile"
        
        return await self._post(endpoint, payload, "Audio", timeout=60.0)
    
    async def send_image(
        self,
        chat_id: str,
        image_url: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an image message
        
        Args:
            chat_id: Chat ID
            image_url: URL to image (JPG, PNG, etc.)
            caption: Optional caption
        """
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
        
        return await self._post("/api/sendImage", payload, "Image", timeout=60.0)
    
    async def send_document(
        self,
        chat_id: str,
        document_url: str,
        filename: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a document/file
        
        Args:
            chat_id: Chat ID
            document_url: URL to document (PDF, DOCX, etc.)
            filename: Display filename
            caption: Optional caption
        """
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
        
        return await self._post("/api/sendFile", payload, "Document", timeout=60.0)
    
    async def send_location(
        self,
        chat_id: str,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a location pin
        
        Args:
            chat_id: Chat ID
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            name: Location name
            address: Location address
        """
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
        
        return await self._post("/api/sendLocation", payload, "Location")
    
    async def send_contact(
        self,
        chat_id: str,
        name: str,
        phone: str
    ) -> Dict[str, Any]:
        """
        Send a contact card
        
        Args:
            chat_id: Chat ID
            name: Contact name
            phone: Phone number
        """
        if "@" not in chat_id:
            chat_id = f"{self._clean_phone(chat_id)}@c.us"
        
        # Format vCard
        vcard = f"""BEGIN:VCARD
VERSION:3.0
FN:{name}
TEL;type=CELL;type=VOICE;waid={phone}:{phone}
END:VCARD"""
        
        payload = {
            "chatId": chat_id,
            "vcard": vcard,
            "session": self.session
        }
        
        return await self._post("/api/sendContact", payload, "Contact")
    
    # ==================== TYPING & READ STATUS ====================
    
    async def mark_as_read(self, chat_id: str) -> bool:
        """Mark messages in a chat as read (blue ticks)"""
        try:
            payload = {
                "chatId": chat_id,
                "session": self.session
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sendSeen",
                    headers=self.headers,
                    json=payload
                )
                return response.status_code in [200, 201]
        except Exception as e:
            logger.debug(f"Mark as read error: {e}")
            return False
    
    async def start_typing(self, chat_id: str) -> bool:
        """Show typing indicator"""
        try:
            payload = {
                "chatId": chat_id,
                "session": self.session
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/startTyping",
                    headers=self.headers,
                    json=payload
                )
                return response.status_code in [200, 201]
        except Exception as e:
            logger.debug(f"Start typing error: {e}")
            return False
    
    async def stop_typing(self, chat_id: str) -> bool:
        """Stop typing indicator"""
        try:
            payload = {
                "chatId": chat_id,
                "session": self.session
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/stopTyping",
                    headers=self.headers,
                    json=payload
                )
                return response.status_code in [200, 201]
        except Exception as e:
            logger.debug(f"Stop typing error: {e}")
            return False
    
    async def start_recording(self, chat_id: str) -> bool:
        """Show 'recording audio' indicator"""
        try:
            payload = {
                "chatId": chat_id,
                "session": self.session
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/startRecording",
                    headers=self.headers,
                    json=payload
                )
                return response.status_code in [200, 201]
        except Exception as e:
            logger.debug(f"Start recording error: {e}")
            return False
    
    async def stop_recording(self, chat_id: str) -> bool:
        """Stop 'recording audio' indicator"""
        try:
            payload = {
                "chatId": chat_id,
                "session": self.session
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/stopRecording",
                    headers=self.headers,
                    json=payload
                )
                return response.status_code in [200, 201]
        except Exception as e:
            logger.debug(f"Stop recording error: {e}")
            return False
    
    # ==================== REACTIONS ====================
    
    async def send_reaction(
        self,
        chat_id: str,
        message_id: str,
        emoji: str
    ) -> Dict[str, Any]:
        """
        React to a message with emoji
        
        Args:
            chat_id: Chat ID
            message_id: ID of message to react to
            emoji: Emoji to react with (e.g., "👍", "❤️", "🤲")
        """
        payload = {
            "chatId": chat_id,
            "messageId": message_id,
            "reaction": emoji,
            "session": self.session
        }
        
        return await self._post("/api/sendReaction", payload, "Reaction")
    
    # ==================== CONTACT INFO ====================
    
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
    
    async def get_profile_picture(self, chat_id: str) -> Optional[str]:
        """Get contact's profile picture URL"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/{self.session}/contacts/{chat_id}/profile-picture",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("profilePictureURL")
                return None
        except Exception as e:
            logger.debug(f"Get profile picture error: {e}")
            return None
    
    # ==================== HELPER METHODS ====================
    
    async def _post(
        self, 
        endpoint: str, 
        payload: Dict[str, Any], 
        action_name: str,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Helper method for POST requests"""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ {action_name} sent to {payload.get('chatId', 'unknown')}")
                    return response.json()
                else:
                    error_text = response.text
                    logger.error(f"❌ {action_name} failed: {response.status_code} - {error_text}")
                    raise Exception(f"{action_name} failed: {response.status_code}")
        
        except httpx.TimeoutException:
            logger.error(f"❌ {action_name} timeout")
            raise
        except Exception as e:
            logger.error(f"❌ {action_name} error: {e}")
            raise
    
    def _clean_phone(self, phone: str) -> str:
        """Clean phone number"""
        phone = phone.split("@")[0] if "@" in phone else phone
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        phone = phone.replace("+", "")
        if phone.startswith("08"):
            phone = "62" + phone[1:]
        return phone
    
    def extract_phone_from_jid(self, jid: str) -> str:
        """Extract phone number from WhatsApp JID"""
        return jid.split("@")[0] if "@" in jid else jid


# ==================== MEDIA ASSETS ====================
# URLs for doa audio files (host on Cloudflare R2 or S3)

DOA_AUDIO_URLS = {
    "niat_umrah": "https://labbaik-assets.example.com/audio/niat_umrah.mp3",
    "talbiyah": "https://labbaik-assets.example.com/audio/talbiyah.mp3",
    "doa_tawaf": "https://labbaik-assets.example.com/audio/doa_tawaf.mp3",
    "doa_sai": "https://labbaik-assets.example.com/audio/doa_sai.mp3",
    "doa_zamzam": "https://labbaik-assets.example.com/audio/doa_zamzam.mp3",
    "doa_masuk_masjid": "https://labbaik-assets.example.com/audio/doa_masuk_masjid.mp3",
    "doa_keluar_masjid": "https://labbaik-assets.example.com/audio/doa_keluar_masjid.mp3",
}

# URLs for infographic images
INFOGRAPHIC_URLS = {
    "tawaf": "https://labbaik-assets.example.com/images/infographic_tawaf.jpg",
    "sai": "https://labbaik-assets.example.com/images/infographic_sai.jpg",
    "ihram": "https://labbaik-assets.example.com/images/infographic_ihram.jpg",
    "checklist": "https://labbaik-assets.example.com/images/infographic_checklist.jpg",
}

# Important locations
LOCATIONS = {
    "masjidil_haram": {
        "lat": 21.4225,
        "lng": 39.8262,
        "name": "Masjidil Haram",
        "address": "Makkah, Saudi Arabia"
    },
    "masjid_nabawi": {
        "lat": 24.4672,
        "lng": 39.6114,
        "name": "Masjid Nabawi",
        "address": "Madinah, Saudi Arabia"
    },
    "kbri_jeddah": {
        "lat": 21.5433,
        "lng": 39.1728,
        "name": "KBRI Jeddah",
        "address": "Jl. Ahmad Lari, Jeddah"
    },
    "kbri_riyadh": {
        "lat": 24.6877,
        "lng": 46.6879,
        "name": "KBRI Riyadh",
        "address": "Diplomatic Quarter, Riyadh"
    }
}
