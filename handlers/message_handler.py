"""
LABBAIK.AI WhatsApp Bot - Message Handler (Enhanced v3)
========================================================
With interactive buttons, audio doa, images, and rich media support
"""

import logging
import re
import asyncio
import random
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date

from services.waha_service import (
    WAHAService, 
    DOA_AUDIO_URLS, 
    INFOGRAPHIC_URLS, 
    LOCATIONS
)
from services.ai_service import AIService
from services.database_service import DatabaseService
from config.settings import settings, MENU_TEMPLATES, DOA_TEMPLATES

logger = logging.getLogger(__name__)


class MessageHandler:
    """Enhanced handler with rich media support"""
    
    # Configuration
    RATE_LIMIT_PER_MINUTE = 10
    DAILY_MESSAGE_LIMIT = 100
    DAILY_AI_CHAT_LIMIT = 30
    MIN_DELAY_AFTER_READ = 1.5
    MAX_DELAY_AFTER_READ = 3.0
    TYPING_DURATION_SHORT = (3, 5)
    TYPING_DURATION_MEDIUM = (5, 8)
    TYPING_DURATION_LONG = (8, 12)
    COOLDOWN_AFTER_LONG_RESPONSE = 2.0
    
    def __init__(
        self,
        waha_service: WAHAService,
        ai_service: AIService,
        db_service: DatabaseService
    ):
        self.waha = waha_service
        self.ai = ai_service
        self.db = db_service
        
        self._user_last_message: Dict[str, datetime] = {}
        self._user_message_count: Dict[str, int] = {}
        self._daily_stats: Dict[str, Dict[str, Any]] = {}
        self._current_date: date = date.today()
        
        # Track user conversation state for multi-step flows
        self._user_state: Dict[str, Dict[str, Any]] = {}
    
    async def handle_incoming_message(self, payload: Dict[str, Any]):
        """Main entry point for handling incoming messages"""
        chat_id = None
        response_sent = False
        
        try:
            message_data = payload.get("payload", {})
            
            if message_data.get("fromMe", False):
                return
            
            from_jid = message_data.get("from", "")
            
            if not from_jid or "status@broadcast" in from_jid:
                return
            
            chat_id = from_jid
            phone = self._extract_phone_for_db(from_jid)
            body = (message_data.get("body") or "").strip()
            message_id = message_data.get("id")
            has_media = message_data.get("hasMedia", False)
            
            # Check for button response
            button_id = message_data.get("selectedButtonId")
            list_id = message_data.get("selectedRowId")
            
            if not body and not has_media and not button_id and not list_id:
                return
            
            # Use button/list ID as body if present
            if button_id:
                body = button_id
                logger.info(f"📩 Button pressed from {chat_id}: {button_id}")
            elif list_id:
                body = list_id
                logger.info(f"📩 List selected from {chat_id}: {list_id}")
            else:
                logger.info(f"📩 Message from {chat_id}: {body[:50]}...")
            
            # Mark as read immediately
            await self.waha.mark_as_read(chat_id)
            
            # Rate limiting
            if not self._check_rate_limit(phone):
                logger.warning(f"⚠️ Rate limit exceeded for {phone}")
                return
            
            # Daily limit check
            daily_check = self._check_daily_limit(phone)
            if not daily_check["allowed"]:
                if not daily_check.get("notified_today"):
                    await self._send_limit_reached_message(chat_id)
                    self._mark_limit_notified(phone)
                return
            
            # Block check
            if await self.db.is_user_blocked(phone):
                return
            
            # Natural delay before typing
            await asyncio.sleep(random.uniform(self.MIN_DELAY_AFTER_READ, self.MAX_DELAY_AFTER_READ))
            await self.waha.start_typing(chat_id)
            
            # Get user info
            user = await self.db.get_or_create_user(phone)
            is_new_user = user.get("is_new", False)
            
            # Classify intent
            intent_result = await self.ai.classify_intent(body)
            intent = intent_result.get("intent", "ai_chat")
            
            # Handle button/list responses
            if button_id or list_id:
                intent, body = self._handle_interactive_response(button_id or list_id)
            
            # Log analytics
            asyncio.create_task(self._log_analytics_safe(phone, intent, body, has_media))
            asyncio.create_task(self._save_conversation_safe(phone, "user", body))
            
            # Route and get response
            if intent == "ai_chat":
                if not self._check_ai_chat_limit(phone):
                    await self._send_ai_limit_message(chat_id)
                    return
                self._increment_ai_chat_count(phone)
            
            # Get response (may be text, buttons, audio, etc.)
            response_data = await self._route_intent_enhanced(intent, body, phone, is_new_user)
            
            # Smart typing delay
            await self._simulate_typing(response_data, chat_id, intent)
            await self.waha.stop_typing(chat_id)
            
            # Random micro-delay
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
            # Send response based on type
            await self._send_response(chat_id, response_data)
            response_sent = True
            
            # Save response
            response_text = response_data.get("text", str(response_data))
            asyncio.create_task(self._save_conversation_safe(phone, "assistant", response_text[:500]))
            
            self._increment_daily_count(phone)
            logger.info(f"✅ Response sent to {chat_id} (type: {response_data.get('type', 'text')})")
            
            # Cooldown
            if len(response_data.get("text", "")) > 1000:
                await asyncio.sleep(self.COOLDOWN_AFTER_LONG_RESPONSE)
        
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}", exc_info=True)
            if chat_id and not response_sent:
                try:
                    await self.waha.stop_typing(chat_id)
                    await asyncio.sleep(1.0)
                    await self.waha.send_message(chat_id, "Mohon maaf, terjadi kesalahan. Ketik *MENU* untuk menu utama.")
                except:
                    pass
    
    # ==================== RESPONSE SENDING ====================
    
    async def _send_response(self, chat_id: str, response_data: Dict[str, Any]):
        """Send response based on type"""
        response_type = response_data.get("type", "text")
        
        if response_type == "text":
            await self.waha.send_message(chat_id, response_data["text"])
        
        elif response_type == "buttons":
            await self.waha.send_buttons(
                chat_id=chat_id,
                text=response_data["text"],
                buttons=response_data["buttons"],
                footer=response_data.get("footer")
            )
        
        elif response_type == "list":
            await self.waha.send_list(
                chat_id=chat_id,
                text=response_data["text"],
                button_text=response_data["button_text"],
                sections=response_data["sections"],
                footer=response_data.get("footer")
            )
        
        elif response_type == "audio":
            # Send text first, then audio
            if response_data.get("text"):
                await self.waha.send_message(chat_id, response_data["text"])
                await asyncio.sleep(0.5)
            
            # Show recording indicator
            await self.waha.start_recording(chat_id)
            await asyncio.sleep(random.uniform(1.5, 2.5))
            await self.waha.stop_recording(chat_id)
            
            await self.waha.send_audio(
                chat_id=chat_id,
                audio_url=response_data["audio_url"],
                as_voice=response_data.get("as_voice", True)
            )
            
            # Send quick replies after audio
            if response_data.get("quick_replies"):
                await asyncio.sleep(0.5)
                await self.waha.send_quick_replies(
                    chat_id=chat_id,
                    text="💡 Doa lainnya:",
                    quick_replies=response_data["quick_replies"]
                )
        
        elif response_type == "image":
            await self.waha.send_image(
                chat_id=chat_id,
                image_url=response_data["image_url"],
                caption=response_data.get("caption")
            )
            
            if response_data.get("follow_up_text"):
                await asyncio.sleep(0.5)
                await self.waha.send_message(chat_id, response_data["follow_up_text"])
        
        elif response_type == "location":
            await self.waha.send_location(
                chat_id=chat_id,
                latitude=response_data["lat"],
                longitude=response_data["lng"],
                name=response_data.get("name"),
                address=response_data.get("address")
            )
            
            if response_data.get("text"):
                await asyncio.sleep(0.3)
                await self.waha.send_message(chat_id, response_data["text"])
        
        elif response_type == "document":
            await self.waha.send_document(
                chat_id=chat_id,
                document_url=response_data["document_url"],
                filename=response_data["filename"],
                caption=response_data.get("caption")
            )
        
        elif response_type == "multi":
            # Send multiple messages in sequence
            for item in response_data["messages"]:
                await self._send_response(chat_id, item)
                await asyncio.sleep(random.uniform(0.8, 1.5))
    
    # ==================== INTERACTIVE RESPONSE HANDLING ====================
    
    def _handle_interactive_response(self, response_id: str) -> Tuple[str, str]:
        """Convert button/list ID to intent and body"""
        mapping = {
            # Main menu buttons
            "menu_guide": ("guide", "panduan"),
            "menu_doa": ("doa", "doa"),
            "menu_cost": ("cost", "biaya"),
            "menu_checklist": ("checklist", "checklist"),
            "menu_visa": ("visa", "visa"),
            "menu_rights": ("rights", "hak jamaah"),
            "menu_agent": ("agent", "travel agent"),
            "menu_ai": ("ai_chat", "chat ai"),
            
            # Guide sub-menu
            "guide_ihram": ("guide", "ihram"),
            "guide_tawaf": ("guide", "tawaf"),
            "guide_sai": ("guide", "sai"),
            "guide_tahallul": ("guide", "tahallul"),
            
            # Doa sub-menu
            "doa_niat": ("doa", "niat umrah"),
            "doa_talbiyah": ("doa", "talbiyah"),
            "doa_tawaf": ("doa", "doa tawaf"),
            "doa_sai": ("doa", "doa sai"),
            "doa_zamzam": ("doa", "doa zamzam"),
            
            # Quick replies
            "qr_0": ("menu", "menu"),
            "qr_1": ("doa", "doa"),
            "qr_2": ("guide", "panduan"),
            
            # Back buttons
            "back_menu": ("menu", "menu"),
            "back_doa": ("doa", "doa menu"),
            "back_guide": ("guide", "panduan menu"),
        }
        
        if response_id in mapping:
            return mapping[response_id]
        
        # Default: treat as text
        return ("ai_chat", response_id)
    
    # ==================== ENHANCED INTENT ROUTING ====================
    
    async def _route_intent_enhanced(
        self,
        intent: str,
        message: str,
        phone: str,
        is_new_user: bool
    ) -> Dict[str, Any]:
        """Route to handler and return rich response data"""
        
        if is_new_user and intent == "greeting":
            return await self._handle_new_user_enhanced()
        
        handlers = {
            "greeting": self._handle_greeting_enhanced,
            "menu": self._handle_menu_enhanced,
            "cost": self._handle_cost_enhanced,
            "guide": self._handle_guide_enhanced,
            "doa": self._handle_doa_enhanced,
            "visa": self._handle_visa_enhanced,
            "checklist": self._handle_checklist_enhanced,
            "rights": self._handle_rights_enhanced,
            "agent": self._handle_agent_enhanced,
            "thanks": self._handle_thanks_enhanced,
            "bye": self._handle_bye_enhanced,
            "ai_chat": self._handle_ai_chat_enhanced,
            "location": self._handle_location,
        }
        
        handler = handlers.get(intent, self._handle_ai_chat_enhanced)
        return await handler(message, phone)
    
    # ==================== ENHANCED HANDLERS ====================
    
    async def _handle_new_user_enhanced(self) -> Dict[str, Any]:
        """Welcome new user with buttons"""
        return {
            "type": "buttons",
            "text": """🕌 *Assalamu'alaikum Warahmatullahi Wabarakatuh!*

Selamat datang di *LABBAIK AI* - Asisten Perencanaan Umrah Indonesia! 🇮🇩

Saya siap membantu Anda merencanakan ibadah Umrah dengan mudah.

Pilih menu di bawah untuk memulai:""",
            "buttons": [
                {"id": "menu_guide", "text": "📖 Panduan Umrah"},
                {"id": "menu_doa", "text": "🤲 Doa & Dzikir"},
                {"id": "menu_cost", "text": "💰 Simulasi Biaya"}
            ],
            "footer": "Atau ketik pertanyaan langsung"
        }
    
    async def _handle_greeting_enhanced(self, message: str, phone: str) -> Dict[str, Any]:
        """Greeting with main menu buttons"""
        return await self._handle_menu_enhanced(message, phone)
    
    async def _handle_menu_enhanced(self, message: str, phone: str) -> Dict[str, Any]:
        """Main menu with interactive list"""
        return {
            "type": "list",
            "text": """🕌 *LABBAIK AI - Menu Utama*

Pilih layanan yang Anda butuhkan:""",
            "button_text": "📋 Lihat Menu",
            "sections": [
                {
                    "title": "📚 Informasi Umrah",
                    "rows": [
                        {"id": "menu_guide", "title": "📖 Panduan Umrah", "description": "Ihram, Tawaf, Sa'i, Tahallul"},
                        {"id": "menu_doa", "title": "🤲 Doa & Dzikir", "description": "Dengan audio bacaan"},
                        {"id": "menu_rights", "title": "⚖️ Hak Jamaah", "description": "29 hak resmi dari Saudi"}
                    ]
                },
                {
                    "title": "💼 Perencanaan",
                    "rows": [
                        {"id": "menu_cost", "title": "💰 Simulasi Biaya", "description": "Estimasi budget umrah"},
                        {"id": "menu_checklist", "title": "✅ Checklist", "description": "Persiapan keberangkatan"},
                        {"id": "menu_visa", "title": "📝 Info Visa", "description": "Persyaratan & proses"}
                    ]
                },
                {
                    "title": "🤖 Lainnya",
                    "rows": [
                        {"id": "menu_agent", "title": "🔍 Cek Travel Agent", "description": "Verifikasi legalitas"},
                        {"id": "menu_ai", "title": "💬 Tanya AI", "description": "Tanya apa saja tentang umrah"}
                    ]
                }
            ],
            "footer": "LABBAIK.AI - labbaik-umrahplanner.streamlit.app"
        }
    
    async def _handle_guide_enhanced(self, message: str, phone: str) -> Dict[str, Any]:
        """Guide menu or specific guide with infographic"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['ihram', 'niat']):
            return await self._get_ihram_guide_enhanced()
        elif any(word in message_lower for word in ['tawaf', 'thawaf']):
            return await self._get_tawaf_guide_enhanced()
        elif any(word in message_lower for word in ['sai', "sa'i"]):
            return await self._get_sai_guide_enhanced()
        elif any(word in message_lower for word in ['tahallul', 'cukur']):
            return await self._get_tahallul_guide_enhanced()
        else:
            # Show guide menu
            return {
                "type": "buttons",
                "text": """📖 *Panduan Tata Cara Umrah*

Pilih panduan yang ingin Anda pelajari:""",
                "buttons": [
                    {"id": "guide_ihram", "text": "1️⃣ Ihram"},
                    {"id": "guide_tawaf", "text": "2️⃣ Tawaf"},
                    {"id": "guide_sai", "text": "3️⃣ Sa'i"}
                ],
                "footer": "Ketik nama rukun untuk detail"
            }
    
    async def _get_ihram_guide_enhanced(self) -> Dict[str, Any]:
        """Ihram guide with image"""
        text = """🕋 *Panduan Ihram*

*Definisi:*
Ihram adalah niat memulai ibadah Umrah dengan memakai pakaian ihram dan mengucapkan niat.

*Langkah-langkah:*

1️⃣ *Persiapan Sebelum Miqat*
   • Mandi (sunnah)
   • Memakai wewangian (sebelum niat)
   • Merapikan kuku, bulu ketiak

2️⃣ *Pakaian Ihram*
   👔 Pria: 2 kain putih tidak berjahit
   👗 Wanita: Pakaian biasa menutup aurat

3️⃣ *Niat di Miqat*
   📖 لَبَّيْكَ اللَّهُمَّ عُمْرَةً
   _"Labbaika Allahumma 'Umratan"_

4️⃣ *Talbiyah* - Dibaca terus sampai tawaf

*Larangan saat Ihram (Pria):*
❌ Pakaian berjahit
❌ Menutup kepala
❌ Wewangian
❌ Potong kuku/rambut"""

        return {
            "type": "multi",
            "messages": [
                {"type": "text", "text": text},
                {
                    "type": "buttons",
                    "text": "🔊 Mau dengar audio niat ihram?",
                    "buttons": [
                        {"id": "doa_niat", "text": "🔊 Audio Niat"},
                        {"id": "doa_talbiyah", "text": "🔊 Audio Talbiyah"},
                        {"id": "back_menu", "text": "📋 Menu Utama"}
                    ]
                }
            ]
        }
    
    async def _get_tawaf_guide_enhanced(self) -> Dict[str, Any]:
        """Tawaf guide"""
        text = """🕋 *Panduan Tawaf*

*Definisi:*
Mengelilingi Ka'bah 7 putaran, dimulai dari Hajar Aswad.

*Langkah-langkah:*

1️⃣ *Persiapan*
   • Berwudhu
   • Idhtiba (bahu kanan terbuka - pria)

2️⃣ *Mulai Tawaf*
   • Sejajarkan dengan Hajar Aswad (lampu hijau)
   • Ucap: _Bismillahi Allahu Akbar_

3️⃣ *7 Putaran*
   • Berlawanan arah jarum jam
   • Ka'bah di sebelah kiri
   • Ramal di 3 putaran awal (pria)

4️⃣ *Doa di Rukun Yamani*
   رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً...

5️⃣ *Setelah Tawaf*
   • Shalat 2 rakaat di Maqam Ibrahim
   • Minum air Zamzam"""

        return {
            "type": "multi",
            "messages": [
                {"type": "text", "text": text},
                {
                    "type": "buttons",
                    "text": "🔊 Dengar doa tawaf?",
                    "buttons": [
                        {"id": "doa_tawaf", "text": "🔊 Audio Doa Tawaf"},
                        {"id": "guide_sai", "text": "➡️ Lanjut Sa'i"},
                        {"id": "back_menu", "text": "📋 Menu Utama"}
                    ]
                }
            ]
        }
    
    async def _get_sai_guide_enhanced(self) -> Dict[str, Any]:
        """Sa'i guide"""
        text = """🏃 *Panduan Sa'i*

*Definisi:*
Berjalan antara Bukit Shafa dan Marwah 7 kali.

*Langkah-langkah:*

1️⃣ *Mulai dari Shafa*
   • Menghadap Ka'bah
   • Baca: إِنَّ الصَّفَا وَالْمَرْوَةَ مِن شَعَائِرِ اللَّهِ

2️⃣ *7 Perjalanan*
   • Shafa → Marwah = 1
   • Marwah → Shafa = 2
   • Berakhir di Marwah (ke-7)

3️⃣ *Lari kecil (Pria)*
   • Di area lampu hijau
   • Wanita jalan biasa

*Info:*
📏 Jarak 1x: 394 meter
📏 Total: 2.761 meter
⏱️ Waktu: 45-55 menit"""

        return {
            "type": "multi",
            "messages": [
                {"type": "text", "text": text},
                {
                    "type": "buttons",
                    "text": "🔊 Dengar doa sa'i?",
                    "buttons": [
                        {"id": "doa_sai", "text": "🔊 Audio Doa Sa'i"},
                        {"id": "guide_tahallul", "text": "➡️ Lanjut Tahallul"},
                        {"id": "back_menu", "text": "📋 Menu Utama"}
                    ]
                }
            ]
        }
    
    async def _get_tahallul_guide_enhanced(self) -> Dict[str, Any]:
        """Tahallul guide"""
        return {
            "type": "text",
            "text": """✂️ *Panduan Tahallul*

*Definisi:*
Mencukur/memotong rambut setelah Sa'i = Umrah selesai!

*Ketentuan:*

👔 *Pria:*
   • Dicukur habis (lebih utama)
   • Atau dipotong merata

👗 *Wanita:*
   • Potong ujung rambut 1-2 cm
   • Tidak boleh dicukur habis

*Lokasi:*
📍 Barbershop sekitar Haram
📍 Di hotel
📍 Potong sendiri

*Setelah Tahallul:*
✅ Larangan ihram selesai
✅ Umrah selesai!

🤲 _Taqabbalallahu minna wa minkum_

Ketik *MENU* untuk kembali."""
        }
    
    async def _handle_doa_enhanced(self, message: str, phone: str) -> Dict[str, Any]:
        """Doa menu or specific doa with audio"""
        message_lower = message.lower()
        
        # Map keywords to doa
        doa_mapping = {
            ('niat', 'niat umrah'): 'niat_umrah',
            ('talbiyah', 'labbaik'): 'talbiyah',
            ('tawaf', 'doa tawaf'): 'doa_tawaf',
            ('sai', "sa'i", 'doa sai'): 'doa_sai',
            ('zamzam', 'doa zamzam'): 'doa_zamzam',
        }
        
        selected_doa = None
        for keywords, doa_key in doa_mapping.items():
            if any(kw in message_lower for kw in keywords):
                selected_doa = doa_key
                break
        
        if selected_doa:
            return await self._get_doa_with_audio(selected_doa)
        
        # Show doa menu
        return {
            "type": "list",
            "text": """🤲 *Doa & Dzikir Umrah*

Pilih doa yang ingin Anda dengar dan pelajari:""",
            "button_text": "📿 Pilih Doa",
            "sections": [
                {
                    "title": "🕋 Doa Wajib Umrah",
                    "rows": [
                        {"id": "doa_niat", "title": "1️⃣ Niat Umrah", "description": "Dibaca saat ihram di Miqat"},
                        {"id": "doa_talbiyah", "title": "2️⃣ Talbiyah", "description": "Labbaikallahumma labbaik..."},
                        {"id": "doa_tawaf", "title": "3️⃣ Doa Tawaf", "description": "Rabbana atina fid-dunya..."},
                        {"id": "doa_sai", "title": "4️⃣ Doa Sa'i", "description": "Di Shafa dan Marwah"},
                        {"id": "doa_zamzam", "title": "5️⃣ Doa Zamzam", "description": "Saat minum air zamzam"}
                    ]
                }
            ],
            "footer": "Setiap doa dilengkapi audio 🔊"
        }
    
    async def _get_doa_with_audio(self, doa_key: str) -> Dict[str, Any]:
        """Get doa text with audio"""
        doa_content = {
            "niat_umrah": {
                "title": "Niat Umrah",
                "arabic": "لَبَّيْكَ اللَّهُمَّ عُمْرَةً",
                "latin": "Labbaikallahumma 'umratan",
                "meaning": "Aku memenuhi panggilan-Mu ya Allah untuk melaksanakan Umrah",
                "when": "Dibaca saat memasuki Miqat"
            },
            "talbiyah": {
                "title": "Talbiyah",
                "arabic": "لَبَّيْكَ اللَّهُمَّ لَبَّيْكَ، لَبَّيْكَ لَا شَرِيْكَ لَكَ لَبَّيْكَ، إِنَّ الْحَمْدَ وَالنِّعْمَةَ لَكَ وَالْمُلْكَ، لَا شَرِيْكَ لَكَ",
                "latin": "Labbaikallahumma labbaik, labbaika laa syariika laka labbaik, innal hamda wan ni'mata laka wal mulk, laa syariika lak",
                "meaning": "Aku memenuhi panggilan-Mu ya Allah. Tiada sekutu bagi-Mu. Segala puji, nikmat dan kerajaan milik-Mu. Tiada sekutu bagi-Mu.",
                "when": "Dibaca terus sejak ihram sampai mulai tawaf"
            },
            "doa_tawaf": {
                "title": "Doa Tawaf",
                "arabic": "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ",
                "latin": "Rabbanaa aatinaa fid-dunyaa hasanatan wa fil-aakhirati hasanatan wa qinaa 'adzaaban-naar",
                "meaning": "Ya Tuhan kami, berilah kami kebaikan di dunia dan di akhirat, dan peliharalah kami dari siksa neraka.",
                "when": "Dibaca antara Rukun Yamani dan Hajar Aswad",
                "source": "QS. Al-Baqarah: 201"
            },
            "doa_sai": {
                "title": "Doa Sa'i di Shafa",
                "arabic": "إِنَّ الصَّفَا وَالْمَرْوَةَ مِن شَعَائِرِ اللَّهِ، أَبْدَأُ بِمَا بَدَأَ اللهُ بِهِ",
                "latin": "Innash-shafaa wal-marwata min sya'aa'irillah, abda'u bimaa bada'allahu bihi",
                "meaning": "Sesungguhnya Shafa dan Marwah adalah syiar Allah. Aku mulai dengan apa yang Allah mulai.",
                "when": "Dibaca di Bukit Shafa dan Marwah",
                "source": "QS. Al-Baqarah: 158"
            },
            "doa_zamzam": {
                "title": "Doa Minum Zamzam",
                "arabic": "اللَّهُمَّ إِنِّي أَسْأَلُكَ عِلْمًا نَافِعًا وَرِزْقًا وَاسِعًا وَشِفَاءً مِنْ كُلِّ دَاءٍ",
                "latin": "Allahumma innii as'aluka 'ilman naafi'an wa rizqan waasi'an wa syifaa'an min kulli daa'",
                "meaning": "Ya Allah, aku memohon ilmu yang bermanfaat, rezeki yang luas, dan kesembuhan dari segala penyakit.",
                "when": "Dibaca saat minum air Zamzam"
            }
        }
        
        doa = doa_content.get(doa_key)
        if not doa:
            return {"type": "text", "text": "Doa tidak ditemukan. Ketik *DOA* untuk menu doa."}
        
        text = f"""🤲 *{doa['title']}*

📖 *Arab:*
{doa['arabic']}

📝 *Latin:*
_{doa['latin']}_

🇮🇩 *Arti:*
{doa['meaning']}

⏰ *Waktu:*
{doa['when']}"""

        if doa.get('source'):
            text += f"\n\n📚 _{doa['source']}_"
        
        # Check if audio exists
        audio_url = DOA_AUDIO_URLS.get(doa_key)
        
        if audio_url and "example.com" not in audio_url:
            return {
                "type": "audio",
                "text": text,
                "audio_url": audio_url,
                "as_voice": True,
                "quick_replies": ["Doa Lainnya", "Panduan", "Menu"]
            }
        else:
            # No audio, just text with buttons
            return {
                "type": "buttons",
                "text": text,
                "buttons": [
                    {"id": "back_doa", "text": "📿 Doa Lainnya"},
                    {"id": "menu_guide", "text": "📖 Panduan"},
                    {"id": "back_menu", "text": "📋 Menu"}
                ]
            }
    
    async def _handle_cost_enhanced(self, message: str, phone: str) -> Dict[str, Any]:
        """Cost simulation with buttons"""
        return {
            "type": "buttons",
            "text": """💰 *Simulasi Biaya Umrah*

Pilih paket untuk melihat estimasi biaya:

*Paket Ekonomi:* Rp 25-32 juta
Hotel 3★, 500m-1km dari Masjid

*Paket Standar:* Rp 32-42 juta
Hotel 4★, 200-500m dari Masjid

*Paket VIP:* Rp 45-75 juta
Hotel 5★, dekat/view Masjid""",
            "buttons": [
                {"id": "cost_ekonomi", "text": "💵 Paket Ekonomi"},
                {"id": "cost_standar", "text": "💳 Paket Standar"},
                {"id": "cost_vip", "text": "💎 Paket VIP"}
            ],
            "footer": "Harga dapat berubah sesuai musim"
        }
    
    async def _handle_visa_enhanced(self, message: str, phone: str) -> Dict[str, Any]:
        """Visa info"""
        return {
            "type": "text",
            "text": """📝 *Informasi Visa Umrah*

*Persyaratan:*
✅ Paspor (min. 6 bulan berlaku)
✅ Foto 4x6 background putih
✅ Vaksin Meningitis (min. 10 hari sebelum)
✅ Bukti booking travel

*Proses:*
📅 Durasi: 3-7 hari kerja
🔍 Tracking: visa.mofa.gov.sa

*Masa Berlaku:*
📆 Single/Multiple entry
⏳ Tinggal maks. 90 hari

*Biaya:*
💰 Biasanya sudah termasuk paket travel

*Tips:*
💡 Pastikan paspor masih valid 6+ bulan
💡 Foto harus terbaru & jelas
💡 Vaksin di KKP atau RS rujukan

Ketik *MENU* untuk kembali."""
        }
    
    async def _handle_checklist_enhanced(self, message: str, phone: str) -> Dict[str, Any]:
        """Checklist"""
        return {
            "type": "text",
            "text": """✅ *Checklist Persiapan Umrah*

*📄 Dokumen:*
☐ Paspor (6+ bulan berlaku)
☐ Visa Umrah
☐ Tiket pesawat PP
☐ Bukti booking hotel
☐ Kartu vaksin
☐ Fotokopi dokumen (2 set)
☐ Pas foto cadangan

*👔 Pakaian Pria:*
☐ Kain ihram 2 set
☐ Sandal ihram
☐ Baju ganti 5-7 set
☐ Jaket/sweater

*👗 Pakaian Wanita:*
☐ Mukena 2-3 set
☐ Jilbab/kerudung
☐ Baju ganti 5-7 set
☐ Kaos kaki

*💊 Kesehatan:*
☐ Obat pribadi
☐ Obat maag/diare
☐ Vitamin
☐ Masker
☐ Hand sanitizer

*📱 Elektronik:*
☐ HP + charger
☐ Power bank
☐ Adaptor (Type G)

*🛍️ Lainnya:*
☐ Uang SAR
☐ Tas kecil
☐ Buku doa
☐ Tasbih

Ketik *MENU* untuk kembali."""
        }
    
    async def _handle_rights_enhanced(self, message: str, phone: str) -> Dict[str, Any]:
        """Jamaah rights"""
        return {
            "type": "text",
            "text": """⚖️ *Hak Jamaah Umrah (29 Hak Resmi)*

*Pelayanan:*
1️⃣ Dilayani dengan amanah & ikhlas
2️⃣ Tracking visa di visa.mofa.gov.sa
3️⃣ Edukasi lengkap sebelum berangkat
4️⃣ Transparansi detail program

*Akomodasi & Transport:*
5️⃣ Penjemputan di bandara
6️⃣ Asuransi komprehensif 90 hari
10. Layanan sesuai kontrak

*Ibadah:*
7️⃣ Pengurusan izin Umrah & Raudhah
8️⃣ Boleh mengulang Umrah (1x Ramadhan)
9️⃣ 1x izin Raudhah per 365 hari

*Darurat:*
23. Layanan darurat 24/7
29. Hotline: +966-920002814

📚 Sumber: Kementerian Haji & Umrah Saudi 1446H

Ketik *HAK [nomor]* untuk detail, misal: HAK 6

Ketik *MENU* untuk kembali."""
        }
    
    async def _handle_agent_enhanced(self, message: str, phone: str) -> Dict[str, Any]:
        """Travel agent verification"""
        return {
            "type": "text",
            "text": """🔍 *Verifikasi Travel Agent*

*Cek di:*
🌐 simpu.kemenag.go.id

*Pastikan:*
✅ Izin resmi dari Kemenag
✅ Terdaftar di SIMPU
✅ Akreditasi masih berlaku
✅ Rekam jejak positif

*🚨 Red Flags:*
❌ Harga terlalu murah
❌ Tidak ada izin resmi
❌ Minta bayar full di awal
❌ Tidak ada kontrak tertulis
❌ Alamat kantor tidak jelas

*💡 Tips:*
• Minta referensi jamaah sebelumnya
• Bandingkan 3+ travel
• Baca kontrak teliti
• Simpan bukti pembayaran

Ketik *MENU* untuk kembali."""
        }
    
    async def _handle_thanks_enhanced(self, message: str, phone: str) -> Dict[str, Any]:
        """Thank you"""
        return {
            "type": "buttons",
            "text": """Sama-sama! 🤲

Senang bisa membantu perencanaan Umrah Anda.

_Semoga Allah memudahkan perjalanan Umrah Anda_""",
            "buttons": [
                {"id": "back_menu", "text": "📋 Menu Utama"},
                {"id": "menu_doa", "text": "🤲 Lihat Doa"},
                {"id": "menu_guide", "text": "📖 Panduan"}
            ]
        }
    
    async def _handle_bye_enhanced(self, message: str, phone: str) -> Dict[str, Any]:
        """Goodbye"""
        return {
            "type": "text",
            "text": """Wa'alaikumussalam Warahmatullahi Wabarakatuh! 👋

Terima kasih telah menggunakan *LABBAIK AI*.

Hubungi kami kapan saja untuk pertanyaan seputar Umrah.

🌐 labbaik-umrahplanner.streamlit.app

_Sampai jumpa, semoga Allah melindungi_ 🤲"""
        }
    
    async def _handle_location(self, message: str, phone: str) -> Dict[str, Any]:
        """Handle location requests"""
        message_lower = message.lower()
        
        if 'kbri' in message_lower and 'jeddah' in message_lower:
            loc = LOCATIONS["kbri_jeddah"]
        elif 'kbri' in message_lower and 'riyadh' in message_lower:
            loc = LOCATIONS["kbri_riyadh"]
        elif 'masjidil haram' in message_lower or 'makkah' in message_lower:
            loc = LOCATIONS["masjidil_haram"]
        elif 'masjid nabawi' in message_lower or 'madinah' in message_lower:
            loc = LOCATIONS["masjid_nabawi"]
        else:
            return {"type": "text", "text": "Lokasi tidak ditemukan. Coba: KBRI Jeddah, Masjidil Haram, dll."}
        
        return {
            "type": "location",
            "lat": loc["lat"],
            "lng": loc["lng"],
            "name": loc["name"],
            "address": loc["address"]
        }
    
    async def _handle_ai_chat_enhanced(self, message: str, phone: str) -> Dict[str, Any]:
        """AI chat"""
        history = await self.db.get_conversation_history(phone, settings.MAX_CONVERSATION_HISTORY)
        response = await self.ai.generate_response(message, conversation_history=history)
        
        return {
            "type": "buttons",
            "text": response,
            "buttons": [
                {"id": "back_menu", "text": "📋 Menu Utama"}
            ],
            "footer": "Powered by LABBAIK AI"
        }
    
    # ==================== UTILITY METHODS ====================
    
    async def _send_limit_reached_message(self, chat_id: str):
        """Send limit message"""
        await self.waha.send_message(chat_id, """⚠️ *Batas Harian Tercapai*

Anda telah mencapai batas penggunaan harian.
Batas reset pukul 00:00 WIB.

🌐 Kunjungi: labbaik-umrahplanner.streamlit.app""")
    
    async def _send_ai_limit_message(self, chat_id: str):
        """Send AI limit message"""
        await self.waha.send_buttons(
            chat_id=chat_id,
            text=f"""⚠️ *Batas AI Chat Tercapai*

Anda telah menggunakan {self.DAILY_AI_CHAT_LIMIT}x AI chat hari ini.

Gunakan menu lain atau tunggu besok.""",
            buttons=[
                {"id": "back_menu", "text": "📋 Menu Utama"},
                {"id": "menu_doa", "text": "🤲 Doa"},
                {"id": "menu_guide", "text": "📖 Panduan"}
            ]
        )
    
    async def _simulate_typing(self, response_data: Dict[str, Any], chat_id: str, intent: str):
        """Simulate typing based on response"""
        response_type = response_data.get("type", "text")
        text_len = len(response_data.get("text", ""))
        
        if response_type in ["audio", "image", "document"]:
            duration = random.uniform(2, 4)
        elif intent in ["greeting", "menu", "thanks", "bye"]:
            duration = random.uniform(*self.TYPING_DURATION_SHORT)
        elif text_len < 500:
            duration = random.uniform(*self.TYPING_DURATION_MEDIUM)
        else:
            duration = random.uniform(*self.TYPING_DURATION_LONG)
        
        elapsed = 0
        while elapsed < duration:
            await asyncio.sleep(min(5.0, duration - elapsed))
            elapsed += 5.0
            if elapsed < duration:
                await self.waha.start_typing(chat_id)
    
    def _extract_phone_for_db(self, jid: str) -> str:
        return jid.split("@")[0] if "@" in jid else jid
    
    def _check_rate_limit(self, phone: str) -> bool:
        now = datetime.now()
        if phone in self._user_last_message:
            if (now - self._user_last_message[phone]).total_seconds() > 60:
                self._user_message_count[phone] = 0
        self._user_last_message[phone] = now
        self._user_message_count[phone] = self._user_message_count.get(phone, 0) + 1
        return self._user_message_count[phone] <= self.RATE_LIMIT_PER_MINUTE
    
    def _reset_daily_stats_if_needed(self):
        today = date.today()
        if today != self._current_date:
            self._daily_stats = {}
            self._current_date = today
    
    def _get_user_daily_stats(self, phone: str) -> Dict[str, Any]:
        self._reset_daily_stats_if_needed()
        if phone not in self._daily_stats:
            self._daily_stats[phone] = {"message_count": 0, "ai_chat_count": 0, "limit_notified": False}
        return self._daily_stats[phone]
    
    def _check_daily_limit(self, phone: str) -> Dict[str, Any]:
        stats = self._get_user_daily_stats(phone)
        if stats["message_count"] >= self.DAILY_MESSAGE_LIMIT:
            return {"allowed": False, "notified_today": stats["limit_notified"]}
        return {"allowed": True}
    
    def _check_ai_chat_limit(self, phone: str) -> bool:
        return self._get_user_daily_stats(phone)["ai_chat_count"] < self.DAILY_AI_CHAT_LIMIT
    
    def _increment_daily_count(self, phone: str):
        self._get_user_daily_stats(phone)["message_count"] += 1
    
    def _increment_ai_chat_count(self, phone: str):
        self._get_user_daily_stats(phone)["ai_chat_count"] += 1
    
    def _mark_limit_notified(self, phone: str):
        self._get_user_daily_stats(phone)["limit_notified"] = True
    
    async def _log_analytics_safe(self, phone: str, intent: str, body: str, has_media: bool):
        try:
            await self.db.log_analytics("message_received", phone, {"intent": intent, "message_length": len(body)})
        except:
            pass
    
    async def _save_conversation_safe(self, phone: str, role: str, content: str):
        try:
            await self.db.save_conversation(phone, role, content)
        except:
            pass
