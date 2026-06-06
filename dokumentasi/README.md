# POS Rental Mobil

Aplikasi POS (Point of Sale) untuk manajemen rental mobil berbasis web. Dibangun dengan Django 6.0.

**URL Production:** [https://rental-pos.onrender.com](https://rental-pos.onrender.com)

## Tech Stack

| Layer | Teknologi |
|-------|-----------|
| Framework | Django 6.0.5 |
| Database | PostgreSQL (Supabase) / SQLite (dev) |
| Storage Foto | Supabase Storage |
| Static Files | Whitenoise |
| Deployment | Render.com + Gunicorn |
| Frontend | Bootstrap 5.3, FullCalendar 6.1 |

## Fitur Utama

- Dashboard ringkasan bisnis bulanan
- Manajemen kendaraan, pelanggan, bengkel
- Order rental dengan invoice otomatis
- Pembayaran multi-metode (tunai, transfer, debit, kredit, QRIS)
- Kalender booking interaktif (drag-drop reschedule)
- Maintenance kendaraan dengan riwayat biaya
- Biaya operasional lain-lain (pajak, alat kantor, dsb)
- Upload foto kendaraan (maks 5, @1MB)
- Laporan keuangan + export CSV
- Rate limiting login admin (anti brute-force)

## Quick Start (Development)

```bash
git clone https://github.com/mimuha/rental-pos.git
cd rental-pos

python -m venv .venv
.venv\Scripts\activate    # Windows
source .venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Buka [http://localhost:8000/admin/](http://localhost:8000/admin/)

## Dokumentasi Lain

- [Daftar Fitur Lengkap](FITUR.md)
- [Model & Relasi](MODEL.md)
- [Deployment (Render.com)](DEPLOY.md)
- [Keamanan / Hardening](SECURITY.md)
