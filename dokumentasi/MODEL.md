# Model & Relasi

## Diagram Relasi

```
Customer ──┐
            │ 1:N
            ├──── Rental ──── Payment (1:N)
            │
Vehicle ───┘
  │
  ├── VehiclePhoto (1:N, managed=False)
  │
  └── VehicleMaintenance (1:N)
        │
        ├── MaintenanceCategory
        └── MaintenanceVendor

VehicleCategory ── Vehicle (1:N)

ExpenseType ── OtherExpense (1:N)
  └── Rental (optional FK)

Rental ── OtherExpense (1:N, SET_NULL)

User ── MenuFavorite (1:N)
```

## Daftar Model

### Customer (Pelanggan)

| Field | Tipe | Keterangan |
|-------|------|------------|
| full_name | CharField(150) | Nama lengkap |
| identity_number | CharField(50), **unique** | Nomor KTP/SIM |
| phone_number | CharField(30) | Nomor telepon |
| email | EmailField | Opsional |
| address | TextField | Alamat |

### VehicleCategory (Kategori Kendaraan)

| Field | Tipe | Keterangan |
|-------|------|------------|
| name | CharField(100), **unique** | Nama kategori |
| description | TextField | Opsional |

### Vehicle (Kendaraan)

| Field | Tipe | Keterangan |
|-------|------|------------|
| category | FK → VehicleCategory, PROTECT | Kategori |
| plate_number | CharField(20), **unique** | Nomor polisi |
| brand | CharField(80) | Merek |
| model | CharField(80) | Model |
| year | PositiveSmallIntegerField | Tahun |
| color | CharField(50) | Warna |
| transmission | CharField(20) | Manual / Automatic |
| fuel_type | CharField(20) | Bensin/Diesel/Listrik/Hybrid |
| seat_count | PositiveSmallIntegerField | Jumlah kursi, default 4 |
| daily_rate | DecimalField(12,2) | Tarif harian (Rp) |
| deposit_amount | DecimalField(12,2) | Uang jaminan |
| odometer | PositiveIntegerField | Km terakhir |
| status | CharField(20) | Tersedia/Disewa/Maintenance/Nonaktif |
| notes | TextField | Catatan |

### VehiclePhoto (Foto Kendaraan)

| Field | Tipe | Keterangan |
|-------|------|------------|
| vehicle | FK → Vehicle, CASCADE | Kendaraan |
| url | URLField(500) | URL foto di Supabase |
| order | IntegerField | Urutan tampilan |
| created_at | DateTimeField | Auto |
| **managed = False** | — | Tabel `vehicle_photos`, batas 5 foto @1MB |

### MaintenanceCategory (Kategori Maintenance)

| Field | Tipe | Keterangan |
|-------|------|------------|
| name | CharField(100), **unique** | Nama |
| category_type | CharField(20) | Oli/Mesin/Kaki-kaki/Accu/Lainnya |
| description | TextField | Opsional |

### MaintenanceVendor (Bengkel)

| Field | Tipe | Keterangan |
|-------|------|------------|
| name | CharField(150), **unique** | Nama bengkel |
| contact_person | CharField(100) | Kontak person |
| phone_number | CharField(30) | Telepon |
| address | TextField | Alamat |
| notes | TextField | Catatan |

### VehicleMaintenance (Maintenance Kendaraan)

| Field | Tipe | Keterangan |
|-------|------|------------|
| vehicle | FK → Vehicle, PROTECT | Kendaraan |
| category | FK → MaintenanceCategory, PROTECT | Kategori |
| vendor | FK → MaintenanceVendor, PROTECT | Bengkel |
| maintenance_date | DateTimeField | Tanggal |
| odometer | PositiveIntegerField | Km saat maintenance |
| issue_description | TextField | Deskripsi masalah |
| parts_replaced | TextField | Sparepart diganti |
| total_cost | DecimalField(12,2) | Total biaya |
| status | CharField(20) | Rencana/Dikerjakan/Selesai/Dibatalkan |
| notes | TextField | Catatan |

### ExpenseType (Jenis Biaya)

| Field | Tipe | Keterangan |
|-------|------|------------|
| name | CharField(100), **unique** | Nama jenis biaya |
| description | TextField | Opsional |

### OtherExpense (Biaya Lain)

| Field | Tipe | Keterangan |
|-------|------|------------|
| expense_type | FK → ExpenseType, PROTECT | Jenis |
| expense_date | DateTimeField | Tanggal |
| payee | CharField(150) | Penerima |
| description | TextField | Deskripsi |
| total_cost | DecimalField(12,2) | Total biaya |
| status | CharField(20) | Rencana/Dikerjakan/Selesai/Dibatalkan |
| invoice_number | CharField(30), **unique** | Auto-generated (expense-YYYY-XXXXX) |
| reference_number | CharField(100) | Nomor referensi |
| notes | TextField | Catatan |
| rental | FK → Rental, SET_NULL | Terkait order rental (auto dari biaya tambahan) |

### Rental (Order Rental)

| Field | Tipe | Keterangan |
|-------|------|------------|
| customer | FK → Customer, PROTECT | Pelanggan |
| vehicle | FK → Vehicle, PROTECT | Kendaraan |
| invoice_number | CharField(30), **unique** | Auto-generated |
| start_at | DateTimeField | Tanggal mulai |
| expected_return_at | DateTimeField | Tanggal kembali |
| returned_at | DateTimeField | Tanggal aktual kembali |
| start_odometer | PositiveIntegerField | Odometer awal |
| end_odometer | PositiveIntegerField | Odometer akhir |
| daily_rate | DecimalField(12,2) | Tarif harian |
| discount_amount | DecimalField(12,2) | Diskon |
| additional_fee | DecimalField(12,2) | Biaya tambahan |
| additional_fee_description | CharField(255) | Uraian biaya tambahan, widget Textarea di admin (opsional) |
| deposit_amount | DecimalField(12,2) | Uang jaminan |
| status | CharField(20) | Draf/Aktif/Selesai/Dibatalkan |
| notes | TextField | Catatan |

**Computed properties:**
- `rental_days` — selisih hari sewa
- `subtotal` — daily_rate × hari
- `total_amount` — subtotal + biaya tambahan - diskon
- `paid_amount` — total pembayaran
- `remaining_amount` — total - sudah dibayar

**Invoice format:** `order-rental-{tahun}-{3 digit urutan}`

### Payment (Pembayaran)

| Field | Tipe | Keterangan |
|-------|------|------------|
| rental | FK → Rental, CASCADE | Order rental |
| payment_date | DateTimeField | Tanggal bayar |
| method | CharField(20) | Tunai/Transfer/Debit/Kredit/QRIS |
| amount | DecimalField(12,2) | Jumlah |
| invoice_number | CharField(30), **unique** | Auto-generated (pay-YYYY-XXXXX) |
| reference_number | CharField(100) | Nomor referensi |
| notes | TextField | Catatan |

### MenuFavorite (Menu Favorit)

| Field | Tipe | Keterangan |
|-------|------|------------|
| user | FK → User, CASCADE | Pemilik favorit |
| menu_key | CharField(100) | Model key (e.g. `vehicle`, `rental`) |
| order | PositiveIntegerField | Urutan tampilan, default 0 |
| **unique_together** | — | `(user, menu_key)` — mencegah duplikat |
| **db_table** | — | `menu_favorites` |

## Otomatisasi Biaya Tambahan → OtherExpense

Saat field `additional_fee` diisi pada form **Order Rental**, sistem otomatis membuat record
`OtherExpense` dengan alur:

1. **Order dibuat** (`additional_fee > 0`) → `OtherExpense` dibuat dengan:
   - `expense_type` = "Biaya Operasional Perjalanan"
   - `status` = **Direncanakan**
   - `total_cost` = nilai `additional_fee`
   - `description` = isian `additional_fee_description` (jika diisi), atau auto `"Biaya tambahan order {invoice}"`

2. **Order diaktifkan** (Draf → Aktif) → status `OtherExpense` berubah ke **Dikerjakan**

3. **Order selesai** (Aktif → Selesai) → status `OtherExpense` berubah ke **Selesai**

4. **`additional_fee` diedit** → `total_cost` di `OtherExpense` ikut disync

5. **`additional_fee_description` diedit** → `description` di `OtherExpense` ikut disync

6. **`additional_fee` jadi 0** → `OtherExpense` terkait otomatis dihapus

> ExpenseType "Biaya Operasional Perjalanan" dibuat otomatis jika belum ada di database.

## Sinkronisasi Status Kendaraan

Saat status **Order Rental** berubah, status **Vehicle** (kendaraan) terkait otomatis diperbarui:

1. **Order diaktifkan** (Draf → Aktif) → status Vehicle berubah dari **Tersedia** → **Disewa**
2. **Order diselesaikan** (Aktif → Selesai) → status Vehicle kembali ke **Tersedia**

> Mekanisme ini berjalan via signal `post_save` pada model Rental di `rentals/signals.py`.

## Field Timestamp (Base)

Semua model di atas (kecuali VehiclePhoto) mewarisi dari `TimeStampedModel`:
- `created_at` — DateTimeField, auto_now_add
- `updated_at` — DateTimeField, auto_now
