"""
LABBAIK.AI WhatsApp Bot - Configuration Settings
=================================================
Environment variables and application settings
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # WAHA Configuration
    WAHA_API_URL: str = "https://waha-qikiufjwa2nh.cgk-max.sumopod.my.id"
    WAHA_SESSION: str = "Labbaik"
    WAHA_API_KEY: Optional[str] = None
    
    # Groq AI Configuration
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MAX_TOKENS: int = 2048
    GROQ_TEMPERATURE: float = 0.7
    
    # Database Configuration (Neon PostgreSQL)
    DATABASE_URL: str = ""
    
    # Application Settings
    APP_NAME: str = "LABBAIK.AI WhatsApp Bot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8000
    
    # Bot Settings
    BOT_NAME: str = "LABBAIK AI"
    BOT_LANGUAGE: str = "id"  # Indonesian
    MAX_CONVERSATION_HISTORY: int = 10
    SESSION_TIMEOUT_MINUTES: int = 30
    
    # Rate Limiting
    MAX_MESSAGES_PER_MINUTE: int = 20
    MAX_AI_REQUESTS_PER_MINUTE: int = 10
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra fields from .env
    }


settings = Settings()


# System prompt for AI
SYSTEM_PROMPT = """Kamu adalah LABBAIK AI, asisten cerdas untuk perencanaan Umrah dari Indonesia. 

## IDENTITAS
- Nama: LABBAIK AI
- Platform: labbaik-umrahplanner.streamlit.app
- Bahasa utama: Indonesia (bisa English jika diminta)
- Gaya komunikasi: Ramah, informatif, Islami

## KEMAMPUAN UTAMA
1. **Panduan Umrah** - Menjelaskan tata cara umrah lengkap (ihram, tawaf, sa'i, tahallul)
2. **Simulasi Biaya** - Estimasi biaya umrah berdasarkan durasi, musim, dan tier
3. **Checklist Persiapan** - Daftar persiapan dokumen, pakaian, kesehatan, dll
4. **Doa & Dzikir** - Memberikan doa dengan Arab, latin, dan terjemahan
5. **Info Visa** - Jenis visa, syarat, dan cara pengajuan
6. **Hak Jamaah** - 29 hak resmi jamaah dari Kementerian Haji Saudi
7. **Lokasi & Transport** - Info Miqat, Haramain Railway, dll

## HAK JAMAAH UMRAH (PENTING)
Berdasarkan dokumen resmi Kementerian Haji & Umrah Saudi 1446H:
- Asuransi komprehensif 90 hari (kesehatan, kecelakaan, delay, repatriasi)
- Penjemputan bandara dan transfer akomodasi
- Transparansi program sebelum pembayaran
- Izin Umrah dan Raudhah diurus oleh travel agent
- Durasi tinggal maksimal 3 bulan
- Pengaduan 24/7: +966-920002814 atau mohcc@haj.gov.sa

## PANDUAN RESPONS
- Selalu mulai dengan salam jika user memberi salam
- Jawab dengan ringkas tapi informatif (max 500 kata)
- Gunakan emoji yang relevan secara wajar 🕌 ✈️ 📋
- Sertakan sumber jika mengutip hadits atau ayat
- Akhiri dengan tawaran bantuan lanjutan
- PENTING: Selalu ingatkan "Do Your Own Research" untuk keputusan penting
- Jangan berikan fatwa, arahkan ke ulama untuk masalah fiqih kompleks

## ESTIMASI BIAYA (REFERENSI)
- Ekonomi: Rp 25-35 juta
- Standar: Rp 35-50 juta  
- Premium: Rp 50-80 juta
- VIP: Rp 80-150 juta
*Harga bervariasi tergantung musim, durasi, dan fasilitas

## FORMAT KHUSUS
Untuk doa, gunakan format:
```
🤲 [Nama Doa]
📖 Arab: [teks Arab]
📝 Latin: [transliterasi]
🇮🇩 Arti: [terjemahan]
📚 Sumber: [referensi]
```

## BATASAN
- Tidak memberikan fatwa atau pendapat fiqih pribadi
- Tidak merekomendasikan travel agent tertentu
- Tidak memproses pembayaran atau booking
- Arahkan ke website untuk fitur lengkap: labbaik-umrahplanner.streamlit.app
"""

# Menu templates
MENU_TEMPLATES = {
    "main": """🕌 *Assalamu'alaikum!*

Saya *LABBAIK AI*, asisten perencanaan Umrah Anda.

📋 *Menu Utama:*
1️⃣ Panduan Umrah
2️⃣ Simulasi Biaya
3️⃣ Checklist Persiapan
4️⃣ Doa & Dzikir
5️⃣ Info Visa
6️⃣ Hak Jamaah
7️⃣ Cek Travel Agent
0️⃣ Bicara dengan AI

💬 Ketik angka atau langsung tanyakan apa saja!

🌐 Website: labbaik-umrahplanner.streamlit.app""",

    "panduan_umrah": """🕋 *Panduan Umrah*

Umrah adalah ibadah mengunjungi Ka'bah dengan:
1. *Ihram* - Niat & berpakaian ihram di Miqat
2. *Tawaf* - Mengelilingi Ka'bah 7 putaran
3. *Sa'i* - Berjalan Shafa-Marwah 7 kali
4. *Tahallul* - Potong/cukur rambut

Ketik untuk detail:
• *IHRAM* - Cara berihram
• *TAWAF* - Panduan tawaf
• *SAI* - Panduan sa'i
• *DOA* - Doa-doa umrah

📖 Atau tanyakan langsung!""",

    "simulasi_biaya": """💰 *Simulasi Biaya Umrah*

Estimasi biaya per orang (2025):

📦 *Paket Ekonomi*
Rp 25-35 juta
Hotel: 500m-1km dari Haram

📦 *Paket Standar*
Rp 35-50 juta
Hotel: 200-500m dari Haram

📦 *Paket Premium*
Rp 50-80 juta
Hotel: <200m, bintang 4-5

📦 *Paket VIP*
Rp 80-150 juta
Hotel: depan Haram, suite

*Termasuk:* Visa, tiket PP, hotel, transport lokal, muthawif

⚠️ Harga bervariasi tergantung musim dan ketersediaan

Mau simulasi detail? Ketik:
SIMULASI [durasi] [bulan] [tier]
Contoh: SIMULASI 9hari Maret standar""",

    "checklist": """✅ *Checklist Persiapan Umrah*

📄 *Dokumen:*
☐ Paspor (min. 6 bulan valid)
☐ Visa Umrah
☐ Tiket pesawat
☐ Bukti booking hotel
☐ Asuransi perjalanan
☐ Foto 4x6 latar putih

👔 *Pakaian (Pria):*
☐ Kain ihram 2 set
☐ Ikat pinggang ihram
☐ Sandal ihram

👗 *Pakaian (Wanita):*
☐ Mukena
☐ Jilbab/kerudung
☐ Gamis longgar

💊 *Kesehatan:*
☐ Obat pribadi
☐ Obat flu & demam
☐ Sunscreen SPF 50+
☐ Bedak anti lecet

📱 *Aplikasi:*
☐ NUSUK
☐ Uber/Careem
☐ Google Maps

Mau checklist lengkap PDF? Kunjungi website kami!""",

    "doa_menu": """🤲 *Doa & Dzikir Umrah*

Pilih doa yang ingin ditampilkan:

1️⃣ Doa Niat Umrah
2️⃣ Talbiyah
3️⃣ Doa Tawaf
4️⃣ Doa Sa'i
5️⃣ Doa Minum Zamzam
6️⃣ Doa Setelah Shalat

Ketik angka atau nama doanya!""",

    "visa_info": """🛂 *Informasi Visa Umrah*

📋 *Jenis Visa:*

1️⃣ *Visa Umrah* (via NUSUK/Travel Agent)
   • Durasi: 90 hari
   • Proses: 1-3 hari kerja

2️⃣ *E-Visa Tourist*
   • Bisa untuk umrah
   • Apply: nusuk.sa
   • Durasi: 1 tahun multiple

3️⃣ *Visa on Arrival*
   • Untuk 49 negara eligible
   • Langsung di bandara Saudi

📝 *Syarat Umum:*
• Paspor min. 6 bulan valid
• Foto latar putih
• Bukti akomodasi
• Tiket PP

🔗 Portal resmi: visa.mofa.gov.sa""",

    "hak_jamaah": """⚖️ *Hak-Hak Jamaah Umrah*

Berdasarkan dokumen resmi Kementerian Haji & Umrah Saudi 1446H:

✅ *Hak Utama:*
1. Layanan dengan amanah & ikhlas
2. Tracking status visa online
3. Edukasi lengkap sebelum berangkat
4. Transparansi program & biaya
5. Penjemputan di bandara
6. Asuransi komprehensif 90 hari
7. Pengurusan izin Umrah & Raudhah
8. Boleh ulang umrah (1x di Ramadhan)

🏥 *Asuransi Mencakup:*
• Kesehatan di semua RS
• Kecelakaan & bencana
• Delay/cancel penerbangan
• Repatriasi jenazah
• COVID-19

📞 *Pengaduan 24/7:*
+966-920002814
mohcc@haj.gov.sa

Ketik HAK [nomor] untuk detail (1-29)""",

    "travel_agent": """🏢 *Verifikasi Travel Agent*

⚠️ Pastikan travel agent Anda resmi!

🔍 *Cara Cek:*
1. Buka: eservices.haj.gov.sa
2. Cari menu "Visa Inquiry"
3. Masukkan nama perusahaan

✅ *Ciri Travel Agent Resmi:*
• Terdaftar di Kemenag RI
• Punya izin PPIU
• Terdaftar di sistem Saudi
• Transparan soal biaya
• Ada kontrak jelas

❌ *Red Flags:*
• Harga terlalu murah
• Tidak ada kantor fisik
• Pembayaran ke rekening pribadi
• Tidak bisa tunjukkan izin

🔗 Cek di: eservices.haj.gov.sa

Butuh bantuan verifikasi? Tanyakan!"""
}

# Doa templates
DOA_TEMPLATES = {
    "niat_umrah": """🤲 *Doa Niat Umrah*

📖 *Arab:*
لَبَّيْكَ اللَّهُمَّ عُمْرَةً

📝 *Latin:*
Labbaika Allahumma 'Umratan

🇮🇩 *Arti:*
Aku penuhi panggilan-Mu ya Allah untuk Umrah

📍 Dibaca di Miqat saat memulai ihram""",

    "talbiyah": """🤲 *Talbiyah*

📖 *Arab:*
لَبَّيْكَ اللَّهُمَّ لَبَّيْكَ، لَبَّيْكَ لَا شَرِيكَ لَكَ لَبَّيْكَ، إِنَّ الْحَمْدَ وَالنِّعْمَةَ لَكَ وَالْمُلْكَ، لَا شَرِيكَ لَكَ

📝 *Latin:*
Labbaika Allahumma labbaik, labbaika la sharika laka labbaik, innal hamda wan-ni'mata laka wal-mulk, la sharika lak

🇮🇩 *Arti:*
Aku penuhi panggilan-Mu ya Allah. Tiada sekutu bagi-Mu. Segala puji, nikmat, dan kerajaan milik-Mu. Tiada sekutu bagi-Mu.

📍 Dibaca terus-menerus sejak ihram hingga mulai tawaf""",

    "doa_tawaf": """🤲 *Doa Tawaf (Antara Rukun Yamani & Hajar Aswad)*

📖 *Arab:*
رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ

📝 *Latin:*
Rabbana atina fid-dunya hasanatan wa fil akhirati hasanatan waqina 'adhaban-nar

🇮🇩 *Arti:*
Ya Tuhan kami, berilah kami kebaikan di dunia dan kebaikan di akhirat, dan lindungilah kami dari siksa neraka

📚 *Sumber:* QS. Al-Baqarah: 201""",

    "doa_sai": """🤲 *Doa di Bukit Shafa/Marwah*

📖 *Arab:*
اللهُ أَكْبَرُ اللهُ أَكْبَرُ اللهُ أَكْبَرُ، لَا إِلٰهَ إِلَّا اللهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ

📝 *Latin:*
Allahu akbar, Allahu akbar, Allahu akbar. La ilaha illallahu wahdahu la sharika lah, lahul mulku wa lahul hamdu wa huwa 'ala kulli shay'in qadir

🇮🇩 *Arti:*
Allah Maha Besar (3x). Tiada Tuhan selain Allah Yang Esa, tiada sekutu bagi-Nya. Milik-Nya kerajaan dan pujian. Dia Maha Kuasa atas segala sesuatu.

📍 Dibaca di atas bukit Shafa dan Marwah menghadap Ka'bah""",

    "doa_zamzam": """🤲 *Doa Minum Air Zamzam*

📖 *Arab:*
اللَّهُمَّ إِنِّي أَسْأَلُكَ عِلْمًا نَافِعًا وَرِزْقًا وَاسِعًا وَشِفَاءً مِنْ كُلِّ دَاءٍ

📝 *Latin:*
Allahumma inni as'aluka 'ilman nafi'an wa rizqan wasi'an wa shifa'an min kulli da'

🇮🇩 *Arti:*
Ya Allah, aku memohon kepada-Mu ilmu yang bermanfaat, rezeki yang luas, dan kesembuhan dari segala penyakit.

📚 *Hadits:* "Air zamzam itu untuk apa ia diminum" (HR. Ahmad)"""
}
