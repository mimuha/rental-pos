# Daftar Fitur

## Dashboard

Halaman utama menampilkan ringkasan bulan berjalan:

- **Total kendaraan** — seluruh unit terdaftar
- **Tersedia** — unit dengan status AVAILABLE
- **Disewa** — unit sedang dirental (status RENTED)
- **Pemasukan bulan ini** — total pembayaran di bulan terpilih
- **Pengeluaran bulan ini** — total maintenance + biaya lain
- Period picker untuk mengganti bulan
- Grup menu akses cepat ke semua modul

## Manajemen Kendaraan

- CRUD kendaraan: nomor polisi, merek, model, tahun, warna, transmisi, bahan bakar, jumlah kursi, tarif harian, uang jaminan, odometer, status
- Filter berdasarkan status, kategori, transmisi, bahan bakar
- Pencarian berdasarkan nomor polisi, merek, model
- **Upload foto kendaraan** via Supabase Storage (maks 5 foto @1MB). UI inline dengan tombol upload, preview thumbnail, dan hapus

## Manajemen Pelanggan

- CRUD pelanggan: nama, nomor identitas, telepon, email, alamat
- Pencarian dan export CSV

## Order Rental

- **Invoice otomatis** format: `Order rental-{tahun}-{nomor_urut}` (contoh: Order rental-2026-001)
- Input: pelanggan, kendaraan, tanggal mulai, tanggal kembali, odometer awal
- Finansial: tarif harian, diskon, biaya tambahan, uraian biaya tambahan (textarea), uang jaminan
- **Kalkulasi real-time** — subtotal dan total terupdate otomatis saat input diubah (client-side JS)
- **Status workflow:** DRAFT → AKTIF (tombol "Aktifkan") → SELESAI (tombol "Selesaikan")
- Validasi tumpang tindih tanggal rental
- Inline pembayaran multi-metode
- **Biaya tambahan otomatis** — field `additional_fee` + `additional_fee_description` otomatis membuat record `OtherExpense` (jenis "Biaya Operasional Perjalanan") dengan status: Direncanakan → Dikerjakan → Selesai, mengikuti status order rental

## Pembayaran

- Metode: Tunai, Transfer Bank, Kartu Debit, Kartu Kredit, QRIS
- Per transaksi bisa banyak pembayaran (angsuran)
- Nomor referensi dan catatan opsional

## Kalender Booking

- Tampilan kalender interaktif untuk semua rental dan maintenance
- Filter per kendaraan dan status rental
- Klik tanggal untuk tambah rental baru (diarahkan ke form dengan tanggal terisi)
- **Drag & drop** untuk mengubah jadwal rental
- Color legend: rental aktif, selesai, dibatalkan, maintenance, ketersediaan

## Maintenance Kendaraan

- Pencatatan maintenance: kendaraan, kategori, bengkel, tanggal, odometer
- Kategori: ganti oli, sparepart mesin, kaki-kaki, service accu, lainnya
- Biaya total per maintenance
- Status workflow: Rencana → Dalam Pengerjaan → Selesai → Dibatalkan
- Riwayat lengkap dengan kolom pencarian

## Manajemen Bengkel

- Daftar bengkel/vendor: nama, kontak person, telepon, alamat

## Biaya Operasional Lain

- Jenis biaya: pajak kendaraan, alat kantor, biaya tak terduga, dll
- Pencatatan: tanggal, penerima, deskripsi, total biaya, nomor referensi
- Status workflow seperti maintenance

## Laporan Keuangan

- Ringkasan periode: total pemasukan, total pengeluaran, laba/rugi
- Rincian transaksi: pembayaran, biaya lain, maintenance
- Tabel interaktif: sorting, pencarian
- **Export CSV** untuk pemrosesan eksternal

## Navigasi Sidebar

- Sidebar admin **collapsed secara default** untuk memaksimalkan area konten
- Tombol ikon pencarian (search) tampil saat sidebar collapsed; klik untuk expand dan langsung fokus ke input pencarian
- Saat sidebar expanded, ikon pencarian di tombol tersembunyi (sudah ada ikon di dalam input form)
- **Shortcut Ctrl+K** — expand sidebar dan fokus ke input pencarian dari mana saja
- Preferensi collapsed/expanded tersimpan di `localStorage` dan diingat antar sesi
- **Menu Favorit** — tombol di bawah search untuk akses cepat ke menu yang sering digunakan
  - Klik untuk melihat daftar menu favorit dalam popup
  - Mode **Edit** untuk menambah/mengurangi menu favorit via checkbox
  - Data favorit tersimpan per-user di database (Supabase PostgreSQL)
  - Tampil di semua mode: expanded, collapsed desktop, dan collapsed mobile
  - Model: `MenuFavorite` (tabel `menu_favorites`)
  - API: `GET/POST /admin/rentals/favorites/`, `POST /admin/rentals/favorites/<id>/delete/`

## Keamanan

- **Rate limiting login admin** — maks 5 percobaan gagal per 15 menit, block 30 menit
- **Auto logout idle** — user otomatis logout setelah tidak ada aktivitas server (lama dikonfigurasi via `DJANGO_SESSION_TIMEOUT`, default 1 jam)
- HTTPS enforced + HSTS 1 tahun + preload
- Secure cookies (session + CSRF)
- ALLOWED_HOSTS dibatasi otomatis via Render
- Credential via environment variables (tidak hardcoded)
