# Keamanan (Hardening)

Dokumentasi langkah keamanan yang telah diterapkan pada aplikasi.

## Transport Security

| Setting | Nilai | Keterangan |
|---------|-------|------------|
| HTTPS | ✅ Enforced | Render meng-terminasi SSL, diteruskan via `SECURE_PROXY_SSL_HEADER` |
| HSTS | ✅ 1 tahun + preload | Browser dipaksa HTTPS selama 1 tahun sejak kunjungan pertama |
| SSL Redirect | ✅ Aktif | HTTP otomatis redirect ke HTTPS |
| Session Cookie | ✅ Secure only | Cookie session hanya dikirim via HTTPS |
| CSRF Cookie | ✅ Secure only | Cookie CSRF hanya dikirim via HTTPS |

## Host & Origin

| Setting | Nilai | Keterangan |
|---------|-------|------------|
| ALLOWED_HOSTS | `RENDER_EXTERNAL_HOSTNAME` | Hanya domain Render yang diizinkan |
| CSRF_TRUSTED_ORIGINS | `https://{RENDER_EXTERNAL_HOSTNAME}` | Origin HTTPS terpercaya |

## Credential Management

| Item | Status |
|------|--------|
| SECRET_KEY | ✅ Environment variable (`DJANGO_SECRET_KEY`), tidak hardcoded |
| DB Password | ✅ Environment variable (`DB_PASSWORD`) |
| Supabase Key | ✅ Environment variable (`SUPABASE_SERVICE_KEY`), format v2 (`sb_secret_...`) |
| Legacy API Keys | ✅ Disabled — JWT `service_role` lama sudah dicabut |
| .env | ✅ Di `.gitignore`, tidak terlacak git |
| .env.example | ✅ Template dokumentasi untuk environment variables |

## Brute Force Protection

- **Rate Limiting Login** via middleware `LoginRateLimitMiddleware`
- Maksimal **5 percobaan gagal** dalam **15 menit** per IP
- IP di-*block* **30 menit** jika melebihi batas (HTTP 429)
- Counter otomatis reset saat login berhasil
- IP asli diambil dari `X-Forwarded-For` hanya jika `TRUSTED_PROXY_COUNT` > 0; jumlah proxy dihitung dari kanan sehingga header palsu dari client tidak bisa dipakai untuk bypass
- Cache rate-limit dapat memakai `REDIS_URL`; tanpa itu dipakai `FileBasedCache` agar counter tetap berlaku lintas worker pada satu host

## Session Idle Timeout

- User otomatis logout setelah tidak ada aktivitas **server** (navigasi halaman, submit form)
- Dikonfigurasi via `DJANGO_SESSION_TIMEOUT`, default **1 jam (3600 detik)**
- Server-side: `SESSION_COOKIE_AGE` + `SESSION_SAVE_EVERY_REQUEST` — session diperbarui setiap request
- Client-side: JavaScript `setTimeout` murni dari halaman dimuat — tanpa reset dari mouse/keyboard
- Keyboard dan mouse **tidak** memperpanjang session — hanya request ke server

## Browser Security Headers

| Header | Status |
|--------|--------|
| X-XSS-Protection | ✅ `SECURE_BROWSER_XSS_FILTER = True` |
| X-Content-Type-Options | ✅ `SECURE_CONTENT_TYPE_NOSNIFF = True` |
| X-Frame-Options | ✅ DENY (via `XFrameOptionsMiddleware`) |
| Strict-Transport-Security | ✅ 1 tahun, include subdomains, preload |

## CSRF Protection

- `CsrfViewMiddleware` aktif
- Setiap form admin dilindungi CSRF token
- AJAX request menyertakan `X-CSRFToken` header (CSRF token dari cookie)

## File Upload

- Batas ukuran: **1 MB** per foto (validasi server-side di `VehiclePhotoForm.clean_image()`)
- Maksimal **5 foto** per kendaraan (validasi server-side di `vehicle_photo_upload`)
- Hanya tipe gambar yang diterima (`accept="image/*"`)

## Debug & Secret

- `DEBUG` dikontrol `DJANGO_DEBUG` (default `False`)
- `DJANGO_SECRET_KEY` wajib diset; aplikasi gagal start jika kosong saat `DEBUG=False`
- `SESSION_COOKIE_SECURE` dan `CSRF_COOKIE_SECURE` otomatis aktif saat `DEBUG=False`

## Rotasi Kredensial (Riwayat)

| Tanggal | Aksi |
|---------|------|
| Jun 2026 | Rotasi Supabase service key: JWT legacy → `sb_secret_...` |
| Jun 2026 | Rotasi DB password |
| Jun 2026 | Disable legacy Supabase API keys |
| Jun 2026 | Generate `DJANGO_SECRET_KEY` baru |

## Rekomendasi untuk Production

- [ ] Pantau log akses admin secara berkala
- [ ] Pertimbangkan 2FA untuk admin jika fitur tersedia
- [ ] Backup database Supabase secara rutin
- [ ] Rotasi kredensial setiap 6 bulan
