# 🕌 LABBAIK.AI WhatsApp Bot

AI-powered Umrah planning assistant via WhatsApp, built with FastAPI and Groq AI.

![Version](https://img.shields.io/badge/version-1.0.0-green)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

## 🌟 Features

- **AI-Powered Chat** - Intelligent responses using Groq AI (Llama 3.3 70B)
- **Umrah Guide** - Complete step-by-step guide for Ihram, Tawaf, Sa'i, Tahallul
- **Cost Simulator** - Estimate Umrah costs based on duration, month, and tier
- **Checklist Generator** - Pre-departure preparation checklist
- **Doa & Dzikir** - Complete prayers with Arabic, transliteration, and translation
- **Visa Information** - Types of visas and requirements
- **Jamaah Rights** - 29 official rights from Saudi Ministry of Hajj
- **Travel Agent Verification** - How to verify licensed agents

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  WhatsApp   │────▶│    WAHA     │────▶│   FastAPI   │
│   Users     │◀────│  (Sumopod)  │◀────│   Webhook   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
              ┌─────▼─────┐            ┌───────▼───────┐          ┌───────▼───────┐
              │  Groq AI  │            │  PostgreSQL   │          │  Knowledge    │
              │  (Chat)   │            │   (Neon)      │          │  Base         │
              └───────────┘            └───────────────┘          └───────────────┘
```

## 📁 Project Structure

```
labbaik-whatsapp-bot/
├── app/
│   └── main.py              # FastAPI application & webhook endpoints
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration, prompts, menu templates
├── handlers/
│   ├── __init__.py
│   └── message_handler.py   # Main message processing logic
├── services/
│   ├── __init__.py
│   ├── waha_service.py      # WAHA API integration
│   ├── ai_service.py        # Groq AI integration
│   └── database_service.py  # PostgreSQL operations
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
├── docker-compose.yml      # Docker Compose setup
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- WAHA instance (running on Sumopod or self-hosted)
- Groq API key ([Get one here](https://console.groq.com/))
- PostgreSQL database (Neon recommended)

### 1. Clone & Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/labbaik-whatsapp-bot.git
cd labbaik-whatsapp-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit with your values
nano .env
```

Required environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `WAHA_API_URL` | Your WAHA instance URL | `https://waha-xxx.sumopod.my.id` |
| `WAHA_SESSION` | WAHA session name | `Labbaik` |
| `GROQ_API_KEY` | Groq API key | `gsk_xxx...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` |

### 3. Run the Bot

```bash
# Development mode
uvicorn app.main:app --reload --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Configure WAHA Webhook

In your WAHA dashboard, set the webhook URL to:

```
https://your-bot-url.com/webhook/waha
```

Events to subscribe:
- `message` - Incoming messages
- `message.ack` - Message acknowledgments
- `session.status` - Session status changes

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Using Docker directly

```bash
# Build image
docker build -t labbaik-wa-bot .

# Run container
docker run -d \
  --name labbaik-wa-bot \
  -p 8000:8000 \
  --env-file .env \
  labbaik-wa-bot
```

## ☁️ Deployment Options

### Option 1: Railway.app (Recommended untuk pemula)

1. Connect your GitHub repository
2. Add environment variables
3. Deploy automatically

### Option 2: Render.com

1. Create new Web Service
2. Connect repository
3. Set environment variables
4. Deploy

### Option 3: VPS (DigitalOcean, Vultr, etc.)

```bash
# SSH to your server
ssh user@your-server

# Clone and setup
git clone https://github.com/yourusername/labbaik-whatsapp-bot.git
cd labbaik-whatsapp-bot

# Using Docker
docker-compose up -d
```

## 📱 Bot Commands & Features

### Menu Structure

```
🕌 LABBAIK AI - Menu Utama

1️⃣ Panduan Umrah    → Ihram, Tawaf, Sa'i, Tahallul
2️⃣ Simulasi Biaya   → Estimasi biaya per tier
3️⃣ Checklist        → Persiapan dokumen, pakaian, dll
4️⃣ Doa & Dzikir     → Talbiyah, doa tawaf, dll
5️⃣ Info Visa        → Jenis visa & syarat
6️⃣ Hak Jamaah       → 29 hak resmi
7️⃣ Cek Travel Agent → Verifikasi agent resmi
0️⃣ Bicara dengan AI → Chat bebas
```

### Example Interactions

**Cost Simulation:**
```
User: SIMULASI 9hari Maret standar
Bot: [Detailed cost breakdown with tips]
```

**Doa Request:**
```
User: doa tawaf
Bot: 🤲 Doa Tawaf
     📖 Arab: رَبَّنَا آتِنَا فِي الدُّنْيَا...
     📝 Latin: Rabbana atina fid-dunya...
     🇮🇩 Arti: Ya Tuhan kami, berilah kami...
```

**AI Chat:**
```
User: Apa beda umrah dan haji?
Bot: [AI-generated comprehensive response]
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/health` | Detailed health status |
| `POST` | `/webhook/waha` | WAHA webhook receiver |
| `POST` | `/webhook/test` | Test endpoint for debugging |
| `POST` | `/api/send-message` | Send message directly |
| `POST` | `/api/broadcast` | Broadcast to multiple users |
| `GET` | `/api/stats` | Bot statistics |

## 📊 Database Schema

```sql
-- Users table
wa_users (
    id, phone, name, first_seen, last_active,
    message_count, preferences, is_blocked
)

-- Conversation history
wa_conversations (
    id, phone, role, content, timestamp, metadata
)

-- Analytics
wa_analytics (
    id, event_type, phone, data, timestamp
)
```

## 🔧 Configuration Options

### AI Settings (config/settings.py)

```python
GROQ_MODEL = "llama-3.3-70b-versatile"  # AI model
GROQ_MAX_TOKENS = 2048                   # Max response length
GROQ_TEMPERATURE = 0.7                   # Creativity (0-1)
MAX_CONVERSATION_HISTORY = 10            # Context messages
```

### Rate Limiting

```python
MAX_MESSAGES_PER_MINUTE = 20    # Per user
MAX_AI_REQUESTS_PER_MINUTE = 10 # AI calls
```

## 🛡️ Security Considerations

- ✅ Enable WAHA API key authentication
- ✅ Use HTTPS for webhook endpoint
- ✅ Implement rate limiting
- ✅ Validate incoming webhook signatures
- ✅ Sanitize user input before AI processing
- ✅ Use environment variables for secrets

## 📈 Monitoring & Logging

Logs are structured and include:
- Incoming message events
- AI response generation
- Error tracking
- Performance metrics

View logs:
```bash
# Docker
docker-compose logs -f labbaik-wa-bot

# Local
tail -f logs/app.log
```

## 🙏 Acknowledgments

- [WAHA](https://waha.devlike.pro/) - WhatsApp HTTP API
- [Groq](https://groq.com/) - Fast AI inference
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- Ministry of Hajj and Umrah - Official documentation

## 📞 Support

- Website: [labbaik-umrahplanner.streamlit.app](https://labbaik-umrahplanner.streamlit.app)
- GitHub Issues

---

**Made with ❤️ for Indonesian Pilgrims**

_Semoga Allah memudahkan perjalanan Umrah Anda_ 🤲
