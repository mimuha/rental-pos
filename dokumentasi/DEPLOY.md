# Deployment (Render.com)

Aplikasi di-deploy di [Render.com](https://render.com) sebagai **Web Service**.

## Ringkasan

| Item | Nilai |
|------|-------|
| URL | [https://rental-pos.onrender.com](https://rental-pos.onrender.com) |
| Branch | `dev` (auto-deploy on push) |
| Region | Singapore |
| WSGI Server | Gunicorn |
| Database | Supabase PostgreSQL (Singapore) |
| Foto Storage | Supabase Storage |

## Build & Start Command

### Build Command
```
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

### Start Command
```
gunicorn rental_pos.wsgi:application --bind 0.0.0.0:$PORT
```

## Environment Variables

Semua environment variable wajib diset di Render dashboard → Environment → Environment Variables.

### Django

| Variable | Keterangan |
|----------|------------|
| `DJANGO_SECRET_KEY` | Secret key Django (wajib 50+ karakter random) |

### Database (Supabase)

| Variable | Keterangan |
|----------|------------|
| `DB_ENGINE` | `postgres` |
| `DB_NAME` | `postgres` |
| `DB_USER` | User database |
| `DB_PASSWORD` | Password database |
| `DB_HOST` | Host pooler Supabase |
| `DB_PORT` | `6543` (pooler) |
| `DB_SSLMODE` | `require` |

### Supabase

| Variable | Keterangan |
|----------|------------|
| `SUPABASE_URL` | URL proyek Supabase |
| `SUPABASE_SERVICE_KEY` | Secret API key (format `sb_secret_...`) |

### HSTS (Opsional — default sudah aktif)

| Variable | Default | Keterangan |
|----------|---------|------------|
| `DJANGO_HSTS_SECONDS` | `31536000` | Durasi HSTS (1 tahun) |
| `DJANGO_HSTS_INCLUDE_SUBDOMAINS` | `True` | |
| `DJANGO_HSTS_PRELOAD` | `True` | |

### SSL

| Variable | Default | Keterangan |
|----------|---------|------------|
| `DJANGO_SECURE_SSL_REDIRECT` | `True` | Redirect HTTP→HTTPS |

> **Catatan:** `RENDER_EXTERNAL_HOSTNAME` diset otomatis oleh Render, tidak perlu ditambah manual. Dipakai untuk `ALLOWED_HOSTS` dan `CSRF_TRUSTED_ORIGINS`.

## Deploy Pertama Kali

1. Push project ke GitHub
2. Di Render dashboard: New → Web Service → connect repo
3. Pilih branch `dev`
4. Isi Build Command dan Start Command (lihat di atas)
5. Tambahkan semua environment variables
6. Klik "Create Web Service"

## Update / Redeploy

Push ke branch `dev` → Render auto-deploy. Atau manual: Render dashboard → Manual Deploy → Deploy latest commit.
