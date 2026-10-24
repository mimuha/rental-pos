"""Index trigram untuk kolom yang dicari dengan `icontains` di admin.

Django admin memakai lookup `icontains` (`LIKE '%kata%'`) yang tidak bisa
memakai index btree biasa. Tanpa bantuan `pg_trgm`, setiap pencarian nama
pelanggan / nopol / nomor invoice berubah menjadi sequential scan.

Ditulis sebagai raw SQL (bukan `GinIndex`) supaya migration tetap berjalan
di SQLite saat pengembangan tanpa PostgreSQL, dan aman diulang.
"""

from django.db import migrations

TRIGRAM_INDEXES = (
    ('rentals_customer_name_trgm_idx', 'rentals_customer', 'full_name'),
    ('rentals_customer_identity_trgm_idx', 'rentals_customer', 'identity_number'),
    ('rentals_customer_phone_trgm_idx', 'rentals_customer', 'phone_number'),
    ('rentals_vehicle_plate_trgm_idx', 'rentals_vehicle', 'plate_number'),
    ('rentals_vehicle_brand_trgm_idx', 'rentals_vehicle', 'brand'),
    ('rentals_vehicle_model_trgm_idx', 'rentals_vehicle', 'model'),
    ('rentals_rental_invoice_trgm_idx', 'rentals_rental', 'invoice_number'),
    ('rentals_payment_invoice_trgm_idx', 'rentals_payment', 'invoice_number'),
    ('rentals_otherexpense_invoice_trgm_idx', 'rentals_otherexpense', 'invoice_number'),
)


def _is_postgres(schema_editor):
    return schema_editor.connection.vendor == 'postgresql'


def create_trigram_indexes(apps, schema_editor):
    if not _is_postgres(schema_editor):
        return

    schema_editor.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    for index_name, table_name, column_name in TRIGRAM_INDEXES:
        schema_editor.execute(
            f'CREATE INDEX IF NOT EXISTS {index_name} '
            f'ON {table_name} USING gin ({column_name} gin_trgm_ops)'
        )


def drop_trigram_indexes(apps, schema_editor):
    if not _is_postgres(schema_editor):
        return

    for index_name, _table_name, _column_name in TRIGRAM_INDEXES:
        schema_editor.execute(f'DROP INDEX IF EXISTS {index_name}')


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0015_otherexpense_other_expense_date_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(create_trigram_indexes, drop_trigram_indexes),
    ]
