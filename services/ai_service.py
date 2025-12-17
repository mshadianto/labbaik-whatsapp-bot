"""
LABBAIK.AI WhatsApp Bot - AI Service
=====================================
Service for AI chat using Groq API
"""

import logging
from typing import List, Dict, Optional
from groq import AsyncGroq
from config.settings import settings, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI chat interactions using Groq"""
    
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
        self.model = settings.GROQ_MODEL
        self.max_tokens = settings.GROQ_MAX_TOKENS
        self.temperature = settings.GROQ_TEMPERATURE
        self.system_prompt = SYSTEM_PROMPT
    
    async def generate_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_name: Optional[str] = None
    ) -> str:
        """
        Generate AI response for user message
        
        Args:
            user_message: The user's message
            conversation_history: Previous messages for context
            user_name: User's name for personalization
        
        Returns:
            AI generated response
        """
        if not self.client:
            logger.error("Groq client not initialized - missing API key")
            return self._get_fallback_response(user_message)
        
        try:
            # Build messages array
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history for context
            if conversation_history:
                # Limit to last N messages to avoid token limits
                recent_history = conversation_history[-settings.MAX_CONVERSATION_HISTORY:]
                messages.extend(recent_history)
            
            # Add current user message
            if user_name:
                user_message = f"[Dari: {user_name}] {user_message}"
            messages.append({"role": "user", "content": user_message})
            
            # Call Groq API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            
            ai_response = response.choices[0].message.content
            logger.info(f"✅ AI response generated ({len(ai_response)} chars)")
            
            return ai_response
        
        except Exception as e:
            logger.error(f"❌ AI generation error: {e}")
            return self._get_fallback_response(user_message)
    
    async def generate_cost_simulation(
        self,
        duration_days: int,
        month: str,
        tier: str
    ) -> str:
        """Generate detailed cost simulation"""
        prompt = f"""Buatkan simulasi biaya umrah dengan detail berikut:
- Durasi: {duration_days} hari
- Bulan keberangkatan: {month}
- Tier paket: {tier}

Berikan estimasi biaya dengan breakdown:
1. Visa
2. Tiket pesawat PP
3. Hotel Makkah
4. Hotel Madinah
5. Transport lokal
6. Handling/muthawif
7. Makan (opsional)
8. Total estimasi

Sertakan catatan tentang faktor yang mempengaruhi harga dan tips menghemat biaya.
Gunakan format yang rapi dengan emoji."""

        return await self.generate_response(prompt)
    
    async def get_doa_explanation(self, doa_name: str) -> str:
        """Get detailed explanation of a doa"""
        prompt = f"""Jelaskan doa "{doa_name}" dengan format:

🤲 Nama Doa
📖 Arab: [teks Arab lengkap]
📝 Latin: [transliterasi]
🇮🇩 Arti: [terjemahan Indonesia]
📍 Waktu/Tempat: [kapan dan dimana dibaca]
📚 Sumber: [referensi hadits/Quran jika ada]
💡 Keutamaan: [fadhilah/keutamaan doa ini]

Pastikan teks Arab dan latin akurat."""

        return await self.generate_response(prompt)
    
    async def answer_fiqh_question(self, question: str) -> str:
        """Answer fiqh-related question with appropriate disclaimer"""
        prompt = f"""Pertanyaan fiqih umrah: {question}

Jawab dengan:
1. Penjelasan umum berdasarkan pendapat mayoritas ulama
2. Sebutkan jika ada perbedaan pendapat
3. Sertakan dalil (ayat/hadits) jika memungkinkan
4. PENTING: Akhiri dengan saran untuk konsultasi ke ustadz/ulama setempat untuk kepastian

Gunakan bahasa yang mudah dipahami dan tidak menggurui."""

        return await self.generate_response(prompt)
    
    async def get_travel_tips(self, topic: str) -> str:
        """Get travel tips for specific topic"""
        prompt = f"""Berikan tips perjalanan umrah tentang: {topic}

Format dengan:
- Tips praktis dan actionable
- Gunakan bullet points
- Sertakan pengalaman umum jamaah
- Berikan alternatif jika ada
- Akhiri dengan reminder penting

Bahasa: Indonesia, gaya: friendly dan helpful"""

        return await self.generate_response(prompt)
    
    def _get_fallback_response(self, user_message: str) -> str:
        """Get fallback response when AI is unavailable"""
        user_lower = user_message.lower()
        
        # Check for common patterns
        if any(word in user_lower for word in ['assalam', 'salam', 'hai', 'halo', 'hi']):
            return """Wa'alaikumussalam warahmatullahi wabarakatuh! 🕌

Mohon maaf, sistem AI sedang dalam maintenance. 

Silakan gunakan menu berikut:
1️⃣ Panduan Umrah
2️⃣ Simulasi Biaya
3️⃣ Checklist
4️⃣ Doa & Dzikir

Atau kunjungi website kami:
🌐 labbaik-umrahplanner.streamlit.app"""
        
        if any(word in user_lower for word in ['biaya', 'harga', 'cost', 'berapa']):
            return """💰 Estimasi Biaya Umrah 2025:

📦 Ekonomi: Rp 25-35 juta
📦 Standar: Rp 35-50 juta
📦 Premium: Rp 50-80 juta
📦 VIP: Rp 80-150 juta

Untuk simulasi detail, kunjungi:
🌐 labbaik-umrahplanner.streamlit.app"""
        
        if any(word in user_lower for word in ['doa', 'dzikir', 'baca']):
            return """🤲 Untuk panduan doa lengkap, ketik:
• TALBIYAH
• DOA TAWAF
• DOA SAI
• DOA ZAMZAM

Atau kunjungi website kami untuk audio dan teks lengkap."""
        
        # Default fallback
        return """Mohon maaf, sistem sedang sibuk. 

Silakan coba lagi atau ketik:
• MENU - untuk menu utama
• HELP - untuk bantuan

🌐 labbaik-umrahplanner.streamlit.app"""
    
    async def classify_intent(self, message: str) -> Dict[str, any]:
        """
        Classify user message intent for routing
        
        Returns:
            Dict with intent, confidence, and entities
        """
        message_lower = message.lower().strip()
        
        # Quick pattern matching for common intents
        patterns = {
            "greeting": ["assalam", "salam", "hai", "halo", "hi", "hello", "pagi", "siang", "sore", "malam"],
            "menu": ["menu", "help", "bantuan", "start", "mulai"],
            "cost": ["biaya", "harga", "cost", "berapa", "simulasi", "estimasi", "budget"],
            "guide": ["panduan", "cara", "tata cara", "gimana", "bagaimana", "langkah", "step"],
            "doa": ["doa", "dzikir", "baca", "talbiyah", "niat"],
            "visa": ["visa", "passport", "paspor", "syarat", "dokumen"],
            "checklist": ["checklist", "persiapan", "bawa", "packing"],
            "rights": ["hak", "rights", "asuransi", "insurance", "komplain"],
            "agent": ["travel", "agent", "biro", "resmi", "legal"],
            "thanks": ["terima kasih", "makasih", "thanks", "syukron"],
            "bye": ["bye", "dadah", "sampai jumpa", "assalamualaikum wr wb"]
        }
        
        for intent, keywords in patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                return {
                    "intent": intent,
                    "confidence": 0.9,
                    "original_message": message
                }
        
        # Default to AI chat for unrecognized messages
        return {
            "intent": "ai_chat",
            "confidence": 0.5,
            "original_message": message
        }
