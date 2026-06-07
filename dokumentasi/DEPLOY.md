# Deployment

Aplikasi dapat di-deploy di platform manapun yang support WSGI/Gunicorn (Render.com, Railway, dsb).

## Ringkasan

| Item | Nilai |
|------|-------|
| WSGI Server | Gunicorn |
| Database | Supabase PostgreSQL |
| Foto Storage | Supabase Storage |
| Static Files | Whitenoise |

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

| Variable | Wajib? | Keterangan |
|----------|--------|------------|
| `DJANGO_SECRET_KEY` | ✅ | Secret key Django (wajib 50+ karakter random) |
| `DJANGO_ALLOWED_HOSTS` | ✅ Production | Domain aplikasi (comma-separated). Contoh: `rental-pos.onrender.com,rental-pos-production.up.railway.app`. Tanpa ini hanya localhost yang diizinkan. |
| `DJANGO_SESSION_TIMEOUT` | ❌ | Auto logout idle (detik), default `3600` (1 jam) |

### Static Files

| Item | Keterangan |
|------|------------|
| Storage | `CompressedStaticFilesStorage` (non-manifest) |
| Finder | `WHITENOISE_USE_FINDERS = True` — Whitenoise langsung serve dari app directory, tidak butuh `collectstatic` |
| Command | `collectstatic --noinput` di build command (opsional tapi disarankan) |

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

> **Catatan:** `DJANGO_ALLOWED_HOSTS` wajib diset di production. Format: domain1,domain2 tanpa spasi setelah koma. Jika tidak diset, hanya `localhost`/`127.0.0.1` yang diizinkan (untuk development).

## Deploy Pertama Kali

1. Push project ke GitHub
2. Di Render dashboard: New → Web Service → connect repo
3. Pilih branch `dev`
4. Isi Build Command dan Start Command (lihat di atas)
5. Tambahkan semua environment variables
6. Klik "Create Web Service"

## Update / Redeploy

Push ke branch `dev` → Render auto-deploy. Atau manual: Render dashboard → Manual Deploy → Deploy latest commit.
