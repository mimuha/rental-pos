# Rental POS

Aplikasi Django 6 berbasis Django Admin untuk POS rental mobil. Tidak ada DRF atau frontend terpisah; UI memakai template admin yang dikustomisasi.

## Commands

```bash
# Test (Postgres dari .env, pakai --keepdb agar cepat)
.venv/Scripts/python.exe manage.py test rentals --noinput --keepdb

# Cek konfigurasi dan migration
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run

# Migration
.venv/Scripts/python.exe manage.py makemigrations rentals
.venv/Scripts/python.exe manage.py migrate
```

Tidak ada linter/formatter yang dikonfigurasi. Jalankan test sebelum commit.

## Struktur

- `rentals/models.py` — model bisnis, invoice sequence, validasi overlap.
- `rentals/signals.py` — sinkronisasi status Rental ke Vehicle dan OtherExpense.
- `rentals/admin.py` — admin, inline, action, laporan keuangan, upload foto.
- `rentals/views.py` — kalender booking dan endpoint reschedule.
- `rentals/forms.py` — form admin, upload Supabase, field uang Rupiah.
- `rentals/dashboard.py` — konteks dashboard dan grouping menu.
- `rental_pos/settings.py` — env, keamanan, cache, database.
- `dokumentasi/` — dokumentasi deploy, model, keamanan, fitur.

## Konvensi bisnis

- Status Rental: DRAFT, ACTIVE, COMPLETED, CANCELLED.
- DRAFT tidak memblokir slot booking dan tidak menandai kalender sibuk. DRAFT tetap divalidasi saat aktivasi.
- Delete rental hanya diizinkan untuk DRAFT. ACTIVE dibatalkan lewat tombol Batalkan (CANCELLED), bukan dihapus.
- CANCELLED mengembalikan Vehicle `RENTED -> AVAILABLE` dan membatalkan OtherExpense PLANNED/IN_PROGRESS.
- Nomor invoice memakai `InvoiceSequence` dengan `select_for_update` dan retry; jangan kembali ke pola query MAX+1.
- `VehiclePhoto` adalah model managed. Migration 0012 membuat tabel `vehicle_photos` bila belum ada.
- Durasi rental memakai `returned_at`, lalu `expected_return_at`. Jangan menambah logika `timezone.now()` sebagai fallback tanpa mengubah kebijakan billing.

## Tema

- Preferensi tema disimpan per user di `UserThemePreference` (`mode`: light/dark/auto, `accent`: purple/orange).
- Atribut `<html>`: `data-theme` dan `data-accent`; diisi context processor `theme_preference`.
- Pilihan tema ada di menu gear pengguna, disimpan lewat `POST /admin/rentals/theme-preference/`.
- Token warna GitLab ada di `rentals/static/rentals/css/gitlab_theme.css`; file ini dimuat setelah `admin-bootstrap.css` dan `dark_mode.css`.
- Palet: blue interaktif `#1f73ca`, purple `#7862c8`, orange `#c74816`, neutral GitLab.
- Ikon logo Zandev tidak diubah. Ikon lain boleh mengikuti `--rental-accent`.
- Hover, selected, focus ring, dan shadow memakai token `--rental-*`; jangan menambah hex baru di komponen.
- Hati-hati specificity: `a:link`/`a:visited` lebih kuat dari `.addlink`. Gunakan `a:where(:link, :visited)` untuk aturan link dasar dan state eksplisit untuk tombol solid.
- Tombol solid wajib teks putih; aksi tambah/sukses memakai `--gl-green-400`.

## Format uang

- Field uang memakai `RupiahField` + `RupiahWidget` dari `rentals/forms.py`.
- Format input/display: titik ribuan dan koma desimal (`1.500.000`, `1.500.000,50`); tanpa `,00` bila bulat.
- Parser server menerima `Rp 2.000.000`, `1.500.000,50`, dan format lama `1500.50`.
- JS `rentals/static/admin/js/rupiah_input.js` memformat live dan mengekspos `window.RupiahFormat.parse`.
- Field uang: `daily_rate`, `deposit_amount`, `discount_amount`, `additional_fee`, `total_cost`, `amount`.

## Gotcha

- `.env` mengarah ke Postgres Supabase; test memakai database `test_postgres`.
- `SECURE_SSL_REDIRECT=True` saat `DEBUG=False`. Test client POST/GET ke admin akan kena 301 kecuali memakai `@override_settings(SECURE_SSL_REDIRECT=False)` atau `secure=True`.
- `DJANGO_SECRET_KEY` wajib saat `DEBUG=False`; aplikasi fail-fast bila kosong.
- `TRUSTED_PROXY_COUNT=1` untuk Render/Railway tanpa Cloudflare; 2 jika ada Cloudflare.
- Rate limit login memakai cache; default `FileBasedCache`, opsional `REDIS_URL`.
- File `__pycache__/*.pyc` masih tracked di repo. Jangan stage perubahan `.pyc`; hanya stage file sumber.
- `testing.html` dan file `*_backup.*` sudah dihapus; jangan menambah artefak serupa ke repo.

## Deploy

- Branch deploy: `dev` (Render auto-deploy).
- Build command harus menjalankan `python manage.py migrate`.
- Static files memakai Whitenoise; database Supabase PostgreSQL; foto di Supabase Storage.
- Render free tier spin-down setelah 15 menit idle; tidak ada heartbeat/pinger internal.
