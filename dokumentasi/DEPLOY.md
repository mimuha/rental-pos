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
| `DJANGO_SECRET_KEY` | ✅ | Secret key Django (wajib 50+ karakter random). Aplikasi gagal start jika kosong saat `DEBUG=False`. |
| `DJANGO_ALLOWED_HOSTS` | ✅ Production | Domain aplikasi (comma-separated). Contoh: `rental-pos.onrender.com,rental-pos-production.up.railway.app`. Tanpa ini hanya localhost yang diizinkan. |
| `DJANGO_DEBUG` | ❌ | Default `False`. Jangan set `True` di production. |
| `DJANGO_SESSION_TIMEOUT` | ❌ | Auto logout idle (detik), default `3600` (1 jam) |
| `TRUSTED_PROXY_COUNT` | ✅ Production | Jumlah reverse proxy tepercaya. `1` untuk Render/Railway, `2` jika ada Cloudflare di depan. Default `0` (X-Forwarded-For diabaikan). |
| `REDIS_URL` | ❌ | Opsional. Bila diisi: cache memakai Redis **dan** sesi memakai `cached_db` (tidak menulis sesi ke database remote di setiap request). Jika kosong, dipakai `FileBasedCache` + sesi database. |
| `DJANGO_CACHE_DIR` | ❌ | Opsional, lokasi cache file-based. Default: direktori temp sistem. |
| `DJANGO_SESSION_SAVE_EVERY_REQUEST` | ❌ | Default `False`. Set `True` untuk perilaku lama (timeout dihitung dari aktivitas terakhir, tetapi menulis sesi ke database di setiap request). |
| `DASHBOARD_CACHE_SECONDS` | ❌ | Default `60`. Lama cache angka dashboard. Set `0` untuk selalu menghitung ulang. |
| `DB_CONN_MAX_AGE` | ❌ | Default `300` detik. Lama koneksi database dipakai ulang antar request. Set `0` untuk membuka koneksi baru tiap request (lambat, tidak disarankan). |

### Static Files

| Item | Keterangan |
|------|------------|
| Storage | `CompressedStaticFilesStorage` (non-manifest) |
| Finder | `WHITENOISE_USE_FINDERS` mengikuti `DJANGO_DEBUG` — saat produksi file dilayani dari `STATIC_ROOT` (hasil `collectstatic`), sehingga build command wajib menjalankan `collectstatic`. |
| Command | `collectstatic --noinput` di build command (wajib, karena finder nonaktif di produksi) |

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
| `DB_CONN_MAX_AGE` | Opsional, default `300` detik. Koneksi dipakai ulang antar request; `0` = buka koneksi baru tiap request (lambat). |

### Index pencarian (pg_trgm)

Migration `0016_trigram_search_indexes` menjalankan `CREATE EXTENSION IF NOT EXISTS pg_trgm`
lalu membuat GIN index untuk kolom yang dicari admin dengan `icontains`
(nama/identitas/telepon pelanggan, nopol/merek/model kendaraan, nomor invoice).

- Butuh role yang boleh `CREATE EXTENSION` (di Supabase: `postgres`), atau aktifkan
  extension `pg_trgm` dari dashboard Supabase lebih dulu.
- Migration tidak melakukan apa pun di SQLite, jadi pengembangan lokal tetap aman.
- Biaya disk: beberapa MB untuk ribuan baris. Kalau kuota free tier mepet, index
  bisa dihapus manual (`DROP INDEX IF EXISTS rentals_customer_name_trgm_idx`) tanpa
  merusak aplikasi — pencarian hanya kembali ke sequential scan.

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
| `DJANGO_SECURE_SSL_REDIRECT` | `True` saat `DEBUG=False` | Redirect HTTP→HTTPS |

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
