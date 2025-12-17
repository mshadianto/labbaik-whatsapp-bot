"""
LABBAIK.AI WhatsApp Bot - Message Handler
==========================================
Main handler for processing incoming WhatsApp messages
"""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime

from services.waha_service import WAHAService
from services.ai_service import AIService
from services.database_service import DatabaseService
from config.settings import settings, MENU_TEMPLATES, DOA_TEMPLATES

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handler for processing incoming WhatsApp messages"""
    
    def __init__(
        self,
        waha_service: WAHAService,
        ai_service: AIService,
        db_service: DatabaseService
    ):
        self.waha = waha_service
        self.ai = ai_service
        self.db = db_service
    
    async def handle_incoming_message(self, payload: Dict[str, Any]):
        """
        Main entry point for handling incoming messages
        
        Args:
            payload: WAHA webhook payload
        """
        try:
            message_data = payload.get("payload", {})
            
            # Skip if message is from the bot itself
            if message_data.get("fromMe", False):
                return
            
            # Extract message details
            from_jid = message_data.get("from", "")
            phone = self.waha.extract_phone_from_jid(from_jid)
            body = message_data.get("body", "").strip()
            message_id = message_data.get("id")
            has_media = message_data.get("hasMedia", False)
            
            # Skip empty messages
            if not body and not has_media:
                return
            
            logger.info(f"📩 Message from {phone}: {body[:50]}...")
            
            # Check if user is blocked
            if await self.db.is_user_blocked(phone):
                logger.info(f"⛔ Blocked user attempted contact: {phone}")
                return
            
            # Get or create user
            user = await self.db.get_or_create_user(phone)
            is_new_user = user.get("is_new", False)
            
            # Show typing indicator
            await self.waha.start_typing(from_jid)
            
            # Mark as read
            await self.waha.mark_as_read(from_jid)
            
            # Classify intent
            intent_result = await self.ai.classify_intent(body)
            intent = intent_result.get("intent", "ai_chat")
            
            # Log analytics
            await self.db.log_analytics("message_received", phone, {
                "intent": intent,
                "message_length": len(body),
                "has_media": has_media
            })
            
            # Save user message to conversation history
            await self.db.save_conversation(phone, "user", body)
            
            # Handle based on intent
            response = await self._route_intent(intent, body, phone, is_new_user)
            
            # Send response
            await self.waha.stop_typing(from_jid)
            await self.waha.send_message(phone, response)
            
            # Save bot response to conversation history
            await self.db.save_conversation(phone, "assistant", response)
            
            logger.info(f"✅ Response sent to {phone}")
        
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
            # Try to send error message
            try:
                await self.waha.send_message(
                    phone,
                    "Mohon maaf, terjadi kesalahan. Silakan coba lagi atau ketik MENU."
                )
            except:
                pass
    
    async def _route_intent(
        self,
        intent: str,
        message: str,
        phone: str,
        is_new_user: bool
    ) -> str:
        """Route message to appropriate handler based on intent"""
        
        # Welcome new users
        if is_new_user and intent == "greeting":
            return await self._handle_new_user()
        
        # Intent routing
        handlers = {
            "greeting": self._handle_greeting,
            "menu": self._handle_menu,
            "cost": self._handle_cost,
            "guide": self._handle_guide,
            "doa": self._handle_doa,
            "visa": self._handle_visa,
            "checklist": self._handle_checklist,
            "rights": self._handle_rights,
            "agent": self._handle_agent,
            "thanks": self._handle_thanks,
            "bye": self._handle_bye,
            "ai_chat": self._handle_ai_chat,
        }
        
        handler = handlers.get(intent, self._handle_ai_chat)
        return await handler(message, phone)
    
    async def _handle_new_user(self) -> str:
        """Handle new user welcome"""
        return """🕌 *Assalamu'alaikum Warahmatullahi Wabarakatuh!*

Selamat datang di *LABBAIK AI* - Asisten Perencanaan Umrah Indonesia! 🇮🇩

Saya siap membantu Anda merencanakan ibadah Umrah dengan mudah dan informatif.

📋 *Yang bisa saya bantu:*
• Panduan tata cara Umrah lengkap
• Simulasi biaya & budgeting
• Checklist persiapan
• Doa-doa Umrah dengan audio
• Info visa & persyaratan
• Hak-hak jamaah resmi

💬 Ketik *MENU* untuk melihat menu lengkap, atau langsung tanyakan apa saja!

🌐 Website: labbaik-umrahplanner.streamlit.app

_Semoga Allah memudahkan perjalanan Umrah Anda_ 🤲"""
    
    async def _handle_greeting(self, message: str, phone: str) -> str:
        """Handle greeting messages"""
        return MENU_TEMPLATES["main"]
    
    async def _handle_menu(self, message: str, phone: str) -> str:
        """Handle menu request"""
        return MENU_TEMPLATES["main"]
    
    async def _handle_cost(self, message: str, phone: str) -> str:
        """Handle cost/pricing inquiries"""
        message_lower = message.lower()
        
        # Check for specific simulation request
        # Format: SIMULASI 9hari Maret standar
        sim_pattern = r'simulasi\s+(\d+)\s*(?:hari|days?)?\s+(\w+)\s+(\w+)'
        match = re.search(sim_pattern, message_lower)
        
        if match:
            duration = int(match.group(1))
            month = match.group(2)
            tier = match.group(3)
            
            # Generate detailed simulation via AI
            return await self.ai.generate_cost_simulation(duration, month, tier)
        
        # Return general cost menu
        return MENU_TEMPLATES["simulasi_biaya"]
    
    async def _handle_guide(self, message: str, phone: str) -> str:
        """Handle umrah guide requests"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['ihram', 'niat']):
            return await self._get_ihram_guide()
        elif any(word in message_lower for word in ['tawaf', 'thawaf']):
            return await self._get_tawaf_guide()
        elif any(word in message_lower for word in ['sai', "sa'i"]):
            return await self._get_sai_guide()
        elif any(word in message_lower for word in ['tahallul', 'cukur', 'potong']):
            return await self._get_tahallul_guide()
        else:
            return MENU_TEMPLATES["panduan_umrah"]
    
    async def _handle_doa(self, message: str, phone: str) -> str:
        """Handle doa/dzikir requests"""
        message_lower = message.lower()
        
        # Check for specific doa
        if any(word in message_lower for word in ['niat', 'niat umrah']):
            return DOA_TEMPLATES["niat_umrah"]
        elif 'talbiyah' in message_lower or 'labbaik' in message_lower:
            return DOA_TEMPLATES["talbiyah"]
        elif 'tawaf' in message_lower:
            return DOA_TEMPLATES["doa_tawaf"]
        elif 'sai' in message_lower or "sa'i" in message_lower:
            return DOA_TEMPLATES["doa_sai"]
        elif 'zamzam' in message_lower:
            return DOA_TEMPLATES["doa_zamzam"]
        elif '1' in message_lower:
            return DOA_TEMPLATES["niat_umrah"]
        elif '2' in message_lower:
            return DOA_TEMPLATES["talbiyah"]
        elif '3' in message_lower:
            return DOA_TEMPLATES["doa_tawaf"]
        elif '4' in message_lower:
            return DOA_TEMPLATES["doa_sai"]
        elif '5' in message_lower:
            return DOA_TEMPLATES["doa_zamzam"]
        else:
            return MENU_TEMPLATES["doa_menu"]
    
    async def _handle_visa(self, message: str, phone: str) -> str:
        """Handle visa inquiries"""
        return MENU_TEMPLATES["visa_info"]
    
    async def _handle_checklist(self, message: str, phone: str) -> str:
        """Handle checklist requests"""
        return MENU_TEMPLATES["checklist"]
    
    async def _handle_rights(self, message: str, phone: str) -> str:
        """Handle jamaah rights inquiries"""
        message_lower = message.lower()
        
        # Check for specific right number
        number_match = re.search(r'hak\s+(\d+)', message_lower)
        if number_match:
            right_num = int(number_match.group(1))
            return await self._get_specific_right(right_num)
        
        return MENU_TEMPLATES["hak_jamaah"]
    
    async def _handle_agent(self, message: str, phone: str) -> str:
        """Handle travel agent verification requests"""
        return MENU_TEMPLATES["travel_agent"]
    
    async def _handle_thanks(self, message: str, phone: str) -> str:
        """Handle thank you messages"""
        return """Sama-sama! 🤲

Senang bisa membantu perencanaan Umrah Anda.

Ada lagi yang bisa saya bantu? Ketik *MENU* untuk menu utama.

_Semoga Allah memudahkan dan mengabulkan niat Umrah Anda_ 🕌"""
    
    async def _handle_bye(self, message: str, phone: str) -> str:
        """Handle goodbye messages"""
        return """Wa'alaikumussalam Warahmatullahi Wabarakatuh! 👋

Terima kasih telah menggunakan LABBAIK AI.

Jangan ragu hubungi kami kapan saja untuk pertanyaan seputar Umrah.

🌐 Website: labbaik-umrahplanner.streamlit.app

_Sampai jumpa, semoga Allah selalu melindungi_ 🤲"""
    
    async def _handle_ai_chat(self, message: str, phone: str) -> str:
        """Handle general AI chat for unrecognized intents"""
        # Get conversation history for context
        history = await self.db.get_conversation_history(
            phone, 
            settings.MAX_CONVERSATION_HISTORY
        )
        
        # Generate AI response
        response = await self.ai.generate_response(
            message,
            conversation_history=history
        )
        
        return response
    
    # ============ Helper methods for detailed content ============
    
    async def _get_ihram_guide(self) -> str:
        """Get detailed ihram guide"""
        return """🕋 *Panduan Ihram*

*Definisi:*
Ihram adalah niat memulai ibadah Umrah dengan memakai pakaian ihram dan mengucapkan niat.

*Langkah-langkah:*

1️⃣ *Persiapan Sebelum Miqat*
   • Mandi (sunnah)
   • Memakai wewangian (sebelum niat)
   • Merapikan kuku, bulu ketiak, dll

2️⃣ *Pakaian Ihram*
   👔 Pria: 2 kain putih tidak berjahit
   👗 Wanita: Pakaian biasa menutup aurat

3️⃣ *Niat di Miqat*
   📖 لَبَّيْكَ اللَّهُمَّ عُمْرَةً
   "Labbaika Allahumma 'Umratan"

4️⃣ *Talbiyah*
   Dibaca terus sampai tawaf

*Larangan saat Ihram (Pria):*
❌ Memakai pakaian berjahit
❌ Menutup kepala
❌ Memakai wewangian
❌ Memotong kuku/rambut

*Lokasi Miqat untuk WNI:*
📍 Bir Ali (dari Madinah)
📍 Yalamlam (via laut)
📍 Pesawat: saat melewati Miqat

Ada pertanyaan tentang ihram?"""
    
    async def _get_tawaf_guide(self) -> str:
        """Get detailed tawaf guide"""
        return """🕋 *Panduan Tawaf*

*Definisi:*
Mengelilingi Ka'bah 7 putaran, dimulai dari Hajar Aswad.

*Langkah-langkah:*

1️⃣ *Persiapan*
   • Berwudhu
   • Idhtiba (bahu kanan terbuka - pria)
   • Posisi: Ka'bah di sebelah kiri

2️⃣ *Mulai Tawaf*
   • Sejajarkan dengan Hajar Aswad
   • Cari lampu hijau sebagai penanda
   • Angkat tangan, ucap "Bismillahi Allahu Akbar"

3️⃣ *7 Putaran*
   • Jalan berlawanan arah jarum jam
   • Ramal (jalan cepat) di 3 putaran awal (pria)
   • Berdoa bebas sepanjang tawaf

4️⃣ *Doa Khusus*
   Antara Rukun Yamani & Hajar Aswad:
   رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً...

5️⃣ *Setelah Tawaf*
   • Tutup bahu (pria)
   • Shalat 2 rakaat di belakang Maqam Ibrahim
   • Minum air Zamzam

*Tips:*
💡 Lantai atas lebih longgar
💡 Hindari foto agar tidak macet
💡 Gunakan app Al Maqsad untuk navigasi

Ketik *DOA TAWAF* untuk doa lengkapnya!"""
    
    async def _get_sai_guide(self) -> str:
        """Get detailed sa'i guide"""
        return """🏃 *Panduan Sa'i*

*Definisi:*
Berjalan antara Bukit Shafa dan Marwah sebanyak 7 kali perjalanan.

*Langkah-langkah:*

1️⃣ *Setelah Tawaf*
   • Minum Zamzam (sunnah)
   • Menuju Shafa

2️⃣ *Di Bukit Shafa*
   • Menghadap Ka'bah
   • Baca: إِنَّ الصَّفَا وَالْمَرْوَةَ مِن شَعَائِرِ اللَّهِ
   • Berdoa

3️⃣ *Jalan ke Marwah*
   • Shafa → Marwah = 1 perjalanan
   • 🏃 Pria: Lari kecil di area lampu hijau
   • Total: 7 perjalanan, berakhir di Marwah

4️⃣ *Di Tiap Bukit*
   • Berdoa menghadap Ka'bah
   • Lanjut ke bukit berikutnya

*Informasi:*
📏 Jarak 1x: 394 meter
📏 Total 7x: 2.761 meter
⏱️ Waktu: 45-55 menit

*Tips:*
💡 Bawa air minum
💡 Gunakan lantai atas jika ramai
💡 Kursi roda tersedia (app Tanaqol)

Ketik *DOA SAI* untuk doa lengkapnya!"""
    
    async def _get_tahallul_guide(self) -> str:
        """Get tahallul guide"""
        return """✂️ *Panduan Tahallul*

*Definisi:*
Mencukur atau memotong rambut setelah selesai Sa'i, menandakan selesainya Umrah.

*Ketentuan:*

👔 *Pria:*
   • Dicukur habis (lebih utama)
   • Atau dipotong merata seluruh kepala
   • Minimal: dipendekkan

👗 *Wanita:*
   • Potong ujung rambut 1-2 cm
   • Tidak boleh dicukur habis

*Lokasi:*
📍 Barbershop berlisensi sekitar Haram
📍 Bisa di hotel
📍 Bisa potong sendiri

*Tips:*
💡 Pilih barbershop berlisensi
💡 Hindari tukang cukur ilegal
💡 Barbershop buka 24 jam di musim ramai

*Setelah Tahallul:*
✅ Larangan ihram selesai
✅ Boleh memakai pakaian biasa
✅ Umrah selesai!

🤲 _Taqabbalallahu minna wa minkum_

Ada pertanyaan lain?"""
    
    async def _get_specific_right(self, right_num: int) -> str:
        """Get specific jamaah right by number"""
        rights = {
            1: "Semua pihak dalam sistem Umrah wajib melayani jamaah dengan amanah dan ikhlas",
            2: "Jamaah dapat melacak status visa melalui visa.mofa.gov.sa",
            3: "Travel agent wajib memberikan edukasi lengkap sebelum keberangkatan",
            4: "Detail program harus transparan sebelum pembayaran",
            5: "Penjemputan di bandara dan transfer ke akomodasi",
            6: "Asuransi komprehensif 90 hari (kesehatan, kecelakaan, delay, repatriasi, COVID)",
            7: "Pengurusan izin Umrah dan shalat di Raudhah",
            8: "Boleh mengulang Umrah selama masa tinggal (1x di Ramadhan)",
            9: "1 izin shalat di Raudhah setiap 365 hari",
            10: "Layanan penuh sesuai kontrak (hotel, transport, ground service)",
            11: "Verifikasi kesiapan layanan sebelum kedatangan",
            12: "Opsi kendaraan pribadi jika tersedia",
            13: "Bantuan jika tersesat untuk kembali ke akomodasi",
            14: "Pengaturan rombongan ke Masjidil Haram & Masjid Nabawi",
            15: "Boleh mengunjungi kota lain di Saudi dengan koordinasi",
            16: "Tinggal maksimal 3 bulan atau sampai 1 Dzulqa'dah",
            23: "Layanan darurat untuk insiden/kesehatan/kematian",
            27: "Perlindungan HAM sesuai regulasi Saudi",
            28: "Boleh melapor ke pihak keamanan jika ada masalah",
            29: "Pengaduan 24/7: +966-920002814 atau mohcc@haj.gov.sa"
        }
        
        if right_num in rights:
            return f"""⚖️ *Hak Jamaah #{right_num}*

{rights[right_num]}

📚 Sumber: Dokumen Hak Jamaah Umrah 1446H
Kementerian Haji & Umrah Saudi Arabia

Ketik HAK untuk melihat daftar lengkap."""
        else:
            return f"Hak nomor {right_num} tidak ditemukan. Ketik HAK untuk daftar lengkap (1-29)."
