# 🔗 Panduan Setup Webhook WAHA untuk LABBAIK Bot

## Langkah 1: Deploy Bot

Pastikan bot sudah running dan accessible via public URL.

**Local Development dengan ngrok:**
```bash
# Install ngrok
# https://ngrok.com/download

# Start bot locally
uvicorn app.main:app --port 8000

# In another terminal, expose with ngrok
ngrok http 8000
```

Ngrok akan memberikan URL seperti: `https://abc123.ngrok.io`

**Production:**
Deploy ke Railway/Render/VPS dan dapatkan URL publik.

## Langkah 2: Configure WAHA Webhook

### Via WAHA Dashboard

1. Buka WAHA Dashboard: `https://waha-qikiufjwa2nh.cgk-max.sumopod.my.id/dashboard`

2. Klik session **Labbaik**

3. Klik icon ⚙️ (Settings/Configure)

4. Cari section **Webhooks**

5. Set webhook URL:
   ```
   https://YOUR-BOT-URL/webhook/waha
   ```

6. Events yang perlu di-enable:
   - ✅ `message` - Pesan masuk
   - ✅ `message.ack` - Status pesan (delivered, read)
   - ✅ `session.status` - Status session

7. Save configuration

### Via WAHA API

```bash
# Set webhook via API
curl -X PUT "https://waha-qikiufjwa2nh.cgk-max.sumopod.my.id/api/sessions/Labbaik" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "webhooks": [
        {
          "url": "https://YOUR-BOT-URL/webhook/waha",
          "events": ["message", "message.ack", "session.status"]
        }
      ]
    }
  }'
```

## Langkah 3: Test Webhook

### Test dengan curl:

```bash
# Test health endpoint
curl https://YOUR-BOT-URL/health

# Test webhook dengan simulated message
curl -X POST "https://YOUR-BOT-URL/webhook/test" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "6281234567890",
    "message": "Assalamualaikum"
  }'
```

### Test dengan WhatsApp:

Kirim pesan ke nomor WhatsApp yang terkoneksi dengan WAHA session **Labbaik**.

## Langkah 4: Verifikasi

1. Cek logs bot:
   ```bash
   # Docker
   docker-compose logs -f
   
   # Local
   # Lihat terminal uvicorn
   ```

2. Cari log seperti:
   ```
   📨 Received webhook: message
   📩 Message from 628xxx: Assalamualaikum...
   ✅ Response sent to 628xxx
   ```

## Troubleshooting

### Webhook tidak diterima

1. **Cek URL accessible:**
   ```bash
   curl https://YOUR-BOT-URL/health
   ```
   
2. **Cek WAHA session status:** Harus `WORKING`

3. **Cek webhook URL di WAHA:** Pastikan tidak ada typo

4. **Cek firewall:** Port harus terbuka

### Bot tidak merespons

1. **Cek GROQ_API_KEY:** Pastikan valid

2. **Cek logs untuk error:**
   ```bash
   docker-compose logs -f | grep -i error
   ```

3. **Cek WAHA connection:**
   ```bash
   curl https://YOUR-BOT-URL/health
   # Lihat status waha: "connected"
   ```

### Response lambat

1. Groq API mungkin sedang sibuk - coba lagi

2. Cek internet connection server

3. Pertimbangkan upgrade ke tier berbayar Groq

## Security Tips

1. **Gunakan HTTPS** - Wajib untuk production

2. **Set WAHA API Key:**
   - Di WAHA, set API key
   - Tambahkan ke `.env`: `WAHA_API_KEY=your-key`

3. **Whitelist IP** (jika memungkinkan):
   - Hanya terima webhook dari IP WAHA

4. **Rate Limiting:**
   - Sudah diimplementasi di bot
   - Adjust di `config/settings.py`

## Arsitektur Webhook Flow

```
[User WhatsApp] 
      ↓ Send Message
[WhatsApp Server]
      ↓ 
[WAHA (Sumopod)]
      ↓ POST /webhook/waha
[LABBAIK Bot (FastAPI)]
      ↓ Process Message
      ↓ Call Groq AI
      ↓ 
[WAHA] ← POST /api/sendText
      ↓
[WhatsApp Server]
      ↓
[User WhatsApp] ← Receive Response
```

---

**Butuh bantuan?** Buka issue di GitHub atau hubungi support.
