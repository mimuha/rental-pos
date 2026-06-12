import re

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField('Dibuat pada', auto_now_add=True)
    updated_at = models.DateTimeField('Diperbarui pada', auto_now=True)

    class Meta:
        abstract = True


class Customer(TimeStampedModel):
    full_name = models.CharField('Nama lengkap', max_length=150)
    identity_number = models.CharField('Nomor identitas', max_length=50, unique=True)
    phone_number = models.CharField('Nomor telepon', max_length=30)
    email = models.EmailField('Email', blank=True)
    address = models.TextField('Alamat')

    class Meta:
        ordering = ['full_name']
        verbose_name = 'Daftar pelanggan'
        verbose_name_plural = 'Daftar pelanggan'

    def __str__(self):
        return self.full_name


class VehicleCategory(TimeStampedModel):
    name = models.CharField('Nama kategori', max_length=100, unique=True)
    description = models.TextField('Deskripsi', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Kategori kendaraan'
        verbose_name_plural = 'Kategori kendaraan'

    def __str__(self):
        return self.name


class Vehicle(TimeStampedModel):
    class Transmission(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        AUTOMATIC = 'automatic', 'Otomatis'

    class FuelType(models.TextChoices):
        GASOLINE = 'gasoline', 'Bensin'
        DIESEL = 'diesel', 'Solar'
        ELECTRIC = 'electric', 'Listrik'
        HYBRID = 'hybrid', 'Hybrid'

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Tersedia'
        RENTED = 'rented', 'Disewa'
        MAINTENANCE = 'maintenance', 'Perawatan'
        INACTIVE = 'inactive', 'Tidak aktif'

    category = models.ForeignKey(
        VehicleCategory,
        on_delete=models.PROTECT,
        related_name='vehicles',
        verbose_name='Kategori kendaraan',
    )
    plate_number = models.CharField('Nomor polisi', max_length=20, unique=True)
    brand = models.CharField('Merek', max_length=80)
    model = models.CharField('Model', max_length=80)
    year = models.PositiveSmallIntegerField('Tahun')
    color = models.CharField('Warna', max_length=50, blank=True)
    transmission = models.CharField('Transmisi', max_length=20, choices=Transmission.choices)
    fuel_type = models.CharField('Jenis bahan bakar', max_length=20, choices=FuelType.choices)
    seat_count = models.PositiveSmallIntegerField('Jumlah kursi', default=4)
    daily_rate = models.DecimalField(
        'Tarif harian (Rp)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    deposit_amount = models.DecimalField(
        'Uang jaminan (Rp)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
    )
    odometer = models.PositiveIntegerField('Odometer')
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    notes = models.TextField('Catatan', blank=True)

    class Meta:
        ordering = ['plate_number']
        verbose_name = 'Daftar kendaraan'
        verbose_name_plural = 'Daftar kendaraan'

    def __str__(self):
        return f'{self.plate_number} - {self.brand} {self.model}'


class VehiclePhoto(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name='Kendaraan',
    )
    url = models.URLField('URL foto', max_length=500)
    order = models.IntegerField('Urutan', default=0)
    created_at = models.DateTimeField('Dibuat pada', auto_now_add=True)

    class Meta:
        db_table = 'vehicle_photos'
        managed = False
        ordering = ['order']
        verbose_name = 'Foto kendaraan'
        verbose_name_plural = 'Foto kendaraan'

    def __str__(self):
        return f'Foto {self.vehicle} - {self.order}'


MAX_PHOTOS_PER_VEHICLE = 5
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB


class MaintenanceCategory(TimeStampedModel):
    class CategoryType(models.TextChoices):
        OIL = 'oil', 'Penggantian oli'
        ENGINE = 'engine', 'Sparepart mesin'
        SUSPENSION = 'suspension', 'Kaki-kaki'
        BATTERY = 'battery', 'Service accu'
        OTHER = 'other', 'Lainnya'

    name = models.CharField('Nama kategori maintenance', max_length=100, unique=True)
    category_type = models.CharField(
        'Jenis maintenance',
        max_length=20,
        choices=CategoryType.choices,
        default=CategoryType.OTHER,
    )
    description = models.TextField('Deskripsi', blank=True)

    class Meta:
        ordering = ['category_type', 'name']
        verbose_name = 'Kategori maintenance'
        verbose_name_plural = 'Kategori maintenance'

    def __str__(self):
        return self.name


class MaintenanceVendor(TimeStampedModel):
    name = models.CharField('Nama bengkel/vendor', max_length=150, unique=True)
    contact_person = models.CharField('Kontak person', max_length=100, blank=True)
    phone_number = models.CharField('Nomor telepon', max_length=30, blank=True)
    address = models.TextField('Alamat', blank=True)
    notes = models.TextField('Catatan', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Daftar bengkel'
        verbose_name_plural = 'Daftar bengkel'

    def __str__(self):
        return self.name


class VehicleMaintenance(TimeStampedModel):
    class Status(models.TextChoices):
        PLANNED = 'planned', 'Direncanakan'
        IN_PROGRESS = 'in_progress', 'Dikerjakan'
        COMPLETED = 'completed', 'Selesai'
        CANCELLED = 'cancelled', 'Dibatalkan'

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name='maintenance_records',
        verbose_name='Daftar Kendaraan',
    )
    category = models.ForeignKey(
        MaintenanceCategory,
        on_delete=models.PROTECT,
        related_name='maintenance_records',
        verbose_name='Kategori maintenance',
    )
    vendor = models.ForeignKey(
        MaintenanceVendor,
        on_delete=models.PROTECT,
        related_name='maintenance_records',
        verbose_name='Daftar bengkel',
    )
    maintenance_date = models.DateTimeField('Tanggal maintenance', default=timezone.now)
    odometer = models.PositiveIntegerField('Odometer', null=True, blank=True)
    issue_description = models.TextField('Masalah / pekerjaan')
    parts_replaced = models.TextField('Sparepart yang diganti', blank=True)
    total_cost = models.DecimalField(
        'Biaya pengeluaran (Rp)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.COMPLETED)
    notes = models.TextField('Catatan', blank=True)

    class Meta:
        ordering = ['-maintenance_date']
        verbose_name = 'Maintenance kendaraan'
        verbose_name_plural = 'Maintenance kendaraan'

    def __str__(self):
        return f'{self.vehicle} - {self.category} - {self.maintenance_date:%d/%m/%Y}'


class ExpenseType(TimeStampedModel):
    name = models.CharField('Nama jenis biaya', max_length=100, unique=True)
    description = models.TextField('Deskripsi', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Jenis biaya'
        verbose_name_plural = 'Jenis biaya'

    def __str__(self):
        return self.name


class OtherExpense(TimeStampedModel):
    class Status(models.TextChoices):
        PLANNED = 'planned', 'Direncanakan'
        IN_PROGRESS = 'in_progress', 'Dikerjakan'
        COMPLETED = 'completed', 'Selesai'
        CANCELLED = 'cancelled', 'Dibatalkan'

    expense_type = models.ForeignKey(
        ExpenseType,
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name='Jenis biaya',
    )
    expense_date = models.DateTimeField('Tanggal biaya', default=timezone.now)
    payee = models.CharField('Penerima / vendor', max_length=150, blank=True)
    description = models.TextField('Uraian biaya')
    total_cost = models.DecimalField(
        'Biaya pengeluaran (Rp)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.COMPLETED)
    reference_number = models.CharField('Nomor referensi', max_length=100, blank=True)
    notes = models.TextField('Catatan', blank=True)
    rental = models.ForeignKey(
        'Rental',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='other_expenses',
        verbose_name='Terkait order rental',
    )

    class Meta:
        ordering = ['-expense_date']
        verbose_name = 'Biaya lain-lain'
        verbose_name_plural = 'Biaya lain-lain'

    def __str__(self):
        return f'{self.expense_type} - {self.expense_date:%d/%m/%Y}'


class Rental(TimeStampedModel):
    INVOICE_PREFIX = 'Order rental'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draf'
        ACTIVE = 'active', 'Aktif'
        COMPLETED = 'completed', 'Selesai'
        CANCELLED = 'cancelled', 'Dibatalkan'

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='rentals',
        verbose_name='Daftar pelanggan',
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name='rentals',
        verbose_name='Daftar kendaraan',
    )
    invoice_number = models.CharField('Nomor invoice', max_length=30, unique=True, blank=True)
    start_at = models.DateTimeField('Mulai sewa')
    expected_return_at = models.DateTimeField('Rencana kembali')
    returned_at = models.DateTimeField('Waktu kembali', null=True, blank=True)
    start_odometer = models.PositiveIntegerField('Odometer awal')
    end_odometer = models.PositiveIntegerField('Odometer akhir', null=True, blank=True)
    daily_rate = models.DecimalField(
        'Tarif harian (Rp)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    discount_amount = models.DecimalField(
        'Diskon (Rp)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
    )
    additional_fee = models.DecimalField(
        'Biaya tambahan (Rp)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
    )
    additional_fee_description = models.CharField('Uraian biaya tambahan', max_length=255, blank=True)
    deposit_amount = models.DecimalField(
        'Uang jaminan (Rp)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
    )
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField('Catatan', blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._previous_status = self.status
        self._previous_additional_fee = self.additional_fee
        self._previous_additional_fee_description = self.additional_fee_description

    class Meta:
        ordering = ['-start_at']
        verbose_name = 'Order rental'
        verbose_name_plural = 'Order rental'

    def __str__(self):
        return f'{self.invoice_number} - {self.customer}'

    def clean(self):
        super().clean()

        if self.start_at and self.expected_return_at and self.expected_return_at <= self.start_at:
            raise ValidationError({
                'expected_return_at': 'Rencana kembali harus setelah mulai sewa.',
            })

        if not (self.vehicle_id and self.start_at and self.expected_return_at):
            return

        overlapping_rentals = Rental.objects.filter(
            vehicle_id=self.vehicle_id,
            start_at__lt=self.expected_return_at,
            expected_return_at__gt=self.start_at,
        ).exclude(
            status=Rental.Status.CANCELLED,
        )
        if self.pk:
            overlapping_rentals = overlapping_rentals.exclude(pk=self.pk)

        if overlapping_rentals.exists():
            raise ValidationError({
                'vehicle': 'Kendaraan sudah memiliki booking pada rentang tanggal tersebut.',
            })

    @classmethod
    def generate_invoice_number(cls, year):
        prefix = f'{cls.INVOICE_PREFIX}-{year}-'
        pattern = re.compile(rf'^{re.escape(prefix)}(\d+)$')
        max_sequence = 0

        invoice_numbers = cls.objects.filter(
            invoice_number__startswith=prefix,
        ).values_list('invoice_number', flat=True)
        for invoice_number in invoice_numbers:
            match = pattern.match(invoice_number)
            if match:
                max_sequence = max(max_sequence, int(match.group(1)))

        return f'{prefix}{max_sequence + 1:03d}'

    def get_invoice_year(self):
        if self.start_at:
            start_at = self.start_at
            if timezone.is_aware(start_at):
                start_at = timezone.localtime(start_at)
            return start_at.year
        return timezone.localdate().year

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number(self.get_invoice_year())
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def rental_days(self):
        if not self.start_at:
            return 0

        end_at = self.returned_at or self.expected_return_at or timezone.now()
        seconds = max((end_at - self.start_at).total_seconds(), 0)
        return max(1, int((seconds + 86399) // 86400))

    @property
    def subtotal(self):
        return (self.daily_rate or Decimal('0')) * self.rental_days

    @property
    def total_amount(self):
        return self.subtotal + (self.additional_fee or Decimal('0')) - (self.discount_amount or Decimal('0'))

    @property
    def paid_amount(self):
        if not self.pk:
            return Decimal('0')

        return sum(payment.amount for payment in self.payments.all())

    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = 'cash', 'Tunai'
        BANK_TRANSFER = 'bank_transfer', 'Transfer bank'
        DEBIT_CARD = 'debit_card', 'Kartu debit'
        CREDIT_CARD = 'credit_card', 'Kartu kredit'
        QRIS = 'qris', 'QRIS'

    rental = models.ForeignKey(
        Rental,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Order rental',
    )
    payment_date = models.DateTimeField('Tanggal pembayaran', default=timezone.now)
    method = models.CharField('Metode pembayaran', max_length=20, choices=Method.choices)
    amount = models.DecimalField(
        'Jumlah pembayaran (Rp)',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    reference_number = models.CharField('Nomor referensi', max_length=100, blank=True)
    notes = models.TextField('Catatan', blank=True)

    class Meta:
        ordering = ['-payment_date']
        verbose_name = 'Order payment'
        verbose_name_plural = 'Order payment'

    def __str__(self):
        return f'{self.rental.invoice_number} - {self.amount}'


class MenuFavorite(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='menu_favorites',
    )
    menu_key = models.CharField('Menu key', max_length=100)
    order = models.PositiveIntegerField('Urutan', default=0)

    class Meta:
        db_table = 'menu_favorites'
        ordering = ['order', 'created_at']
        unique_together = [('user', 'menu_key')]
        verbose_name = 'Menu favorit'
        verbose_name_plural = 'Menu favorit'

    def __str__(self):
        return f'{self.user} - {self.menu_key}'
