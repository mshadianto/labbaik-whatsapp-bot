FROM python:3.11-slim

WORKDIR /app

# Mencegah Python membuat file .pyc dan buffering stdout (bagus untuk log)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependency sistem
# gcc: sering dibutuhkan untuk build library python tertentu
# curl: dibutuhkan untuk perintah HEALTHCHECK di bawah
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependency Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode aplikasi
COPY . .

# Buat user non-root demi keamanan
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (hanya dokumentasi)
EXPOSE 8000

# Healthcheck
# Pastikan endpoint /health sudah dibuat di main.py Anda
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=5 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# PERINTAH UTAMA (Shell Form)
# Tidak menggunakan tanda kurung [] agar variabel ${PORT} terbaca oleh shell
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
