from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.urls import reverse
from django.utils import timezone

from .cache_utils import safe_cache_get, safe_cache_set
from .models import OtherExpense, Payment, Rental, Vehicle, VehicleMaintenance


def month_bounds(year, month):
    """Rentang [awal bulan, awal bulan berikutnya) dalam timezone lokal.

    Dipakai menggantikan lookup `__year`/`__month` yang membuat Postgres
    mengevaluasi EXTRACT() per baris sehingga index tanggal tidak terpakai.
    """
    current_tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime(year, month, 1), current_tz)
    if month == 12:
        end = timezone.make_aware(datetime(year + 1, 1, 1), current_tz)
    else:
        end = timezone.make_aware(datetime(year, month + 1, 1), current_tz)
    return start, end


RENTAL_MENU_GROUPS = (
    (
        'Master Data',
        (
            'maintenancevendor',
            'vehicle',
            'customer',
            'vehiclecategory',
            'maintenancecategory',
        ),
    ),
    (
        'Transaksi',
        (
            'vehiclemaintenance',
            'rental',
            'payment',
            'bookingcalendar',
        ),
    ),
    (
        'Keuangan',
        (
            'otherexpense',
            'expensetype',
            'financialreport',
        ),
    ),
)

INDONESIAN_MONTHS = (
    'Januari',
    'Februari',
    'Maret',
    'April',
    'Mei',
    'Juni',
    'Juli',
    'Agustus',
    'September',
    'Oktober',
    'November',
    'Desember',
)


def format_rupiah(value):
    if value is None:
        value = 0

    amount = f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    if amount.endswith(',00'):
        amount = amount[:-3]
    return f'Rp{amount}'


def format_rupiah_short(value):
    if value is None:
        value = Decimal('0')
    value = Decimal(str(value))

    thresholds = [
        (Decimal('1000000000000'), 'T'),
        (Decimal('1000000000'), 'M'),
        (Decimal('1000000'), 'jt'),
        (Decimal('1000'), 'rb'),
    ]

    for threshold, suffix in thresholds:
        if value >= threshold:
            divided = value / threshold
            rounded = divided.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            text = str(rounded)
            if '.' in text:
                text = text.rstrip('0').rstrip('.')
            text = text.replace('.', ',')
            return f'Rp {text}{suffix}'

    return f'Rp {int(value)}'


def parse_dashboard_period(request):
    now = timezone.localtime()
    default = (now.year, now.month)
    raw = request.GET.get('period', '').strip()
    if not raw:
        return default

    parts = raw.split('-')
    if len(parts) != 2:
        return default

    try:
        year = int(parts[0])
        month = int(parts[1])
    except ValueError:
        return default

    if not (1 <= month <= 12 and 2000 <= year <= 2100):
        return default

    return year, month


def format_period_label(year, month):
    return f'{INDONESIAN_MONTHS[month - 1]} {year}'


def financial_report_menu_model():
    return {
        'object_name': 'financialreport',
        'name': 'Laporan Keuangan',
        'admin_url': reverse('admin:rental_financial_report'),
        'add_url': None,
    }


def booking_calendar_menu_model():
    return {
        'object_name': 'bookingcalendar',
        'name': 'Kalender Booking',
        'admin_url': reverse('admin:rental_booking_calendar'),
        'add_url': None,
    }


def group_rental_menu(models):
    models_by_name = {
        model['object_name'].lower(): model
        for model in models
    }
    if 'financialreport' not in models_by_name:
        models_by_name['financialreport'] = financial_report_menu_model()
    if 'bookingcalendar' not in models_by_name:
        models_by_name['bookingcalendar'] = booking_calendar_menu_model()

    groups = []

    for title, model_names in RENTAL_MENU_GROUPS:
        items = [models_by_name[name] for name in model_names if name in models_by_name]
        if items:
            groups.append({'title': title, 'models': items})

    grouped_names = {
        name
        for _, model_names in RENTAL_MENU_GROUPS
        for name in model_names
    }
    remaining = [
        model
        for name, model in models_by_name.items()
        if name not in grouped_names
    ]
    if remaining:
        groups.append({'title': 'Lainnya', 'models': remaining})

    return groups


def apply_rental_menu_groups(app_list):
    for app in app_list:
        if app['app_label'] == 'rentals':
            app['menu_groups'] = group_rental_menu(app['models'])
    return app_list


ATTENTION_LIMIT = 5
AGENDA_DAYS = 7
AGENDA_LIMIT = 8
FLEET_LIMIT = 6
CHART_MONTHS = 6

MONTH_SHORT = ('Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des')


def _short_date(value):
    local = timezone.localtime(value) if timezone.is_aware(value) else value
    return f'{local.day} {MONTH_SHORT[local.month - 1]}'


def _shift_month(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def get_active_rentals():
    return list(
        Rental.objects.filter(status=Rental.Status.ACTIVE)
        .select_related('customer', 'vehicle')
        .prefetch_related('payments')
        .order_by('expected_return_at')
    )


def get_draft_rentals():
    return list(
        Rental.objects.filter(status=Rental.Status.DRAFT)
        .select_related('customer', 'vehicle')
        .order_by('start_at')
    )


def get_attention_items(maintenance_count=0, now=None, active_rentals=None, draft_rentals=None):
    """Hal yang butuh tindakan kasir: telat kembali, belum lunas, draf, perawatan.

    Mengembalikan struktur dict/list biasa agar aman disimpan di cache.
    """
    now = now or timezone.now()
    if active_rentals is None:
        active_rentals = get_active_rentals()
    if draft_rentals is None:
        draft_rentals = get_draft_rentals()

    def rental_item(rental, detail, action_label, action_url):
        return {
            'title': f'{rental.invoice_number} - {rental.customer.full_name}',
            'detail': detail,
            'url': reverse('admin:rentals_rental_change', args=[rental.pk]),
            'action_label': action_label,
            'action_url': action_url,
        }

    def change_url(rental):
        return reverse('admin:rentals_rental_change', args=[rental.pk])

    overdue = [
        rental for rental in active_rentals
        if rental.expected_return_at and rental.expected_return_at < now
    ]
    unpaid = [rental for rental in active_rentals if rental.remaining_amount > 0]
    soon = now + timedelta(days=AGENDA_DAYS)
    drafts = [rental for rental in draft_rentals if rental.start_at and rental.start_at <= soon]

    return {
        'overdue_count': len(overdue),
        'overdue': [
            rental_item(
                rental,
                f'{rental.vehicle.plate_number}, seharusnya kembali '
                f'{timezone.localtime(rental.expected_return_at):%d/%m/%Y %H:%M}',
                'Selesaikan',
                change_url(rental),
            )
            for rental in overdue[:ATTENTION_LIMIT]
        ],
        'unpaid_count': len(unpaid),
        'unpaid': [
            rental_item(
                rental,
                f'Sisa {format_rupiah(rental.remaining_amount)}',
                'Catat bayar',
                f"{reverse('admin:rentals_payment_add')}?rental={rental.pk}",
            )
            for rental in unpaid[:ATTENTION_LIMIT]
        ],
        'draft_count': len(drafts),
        'drafts': [
            rental_item(
                rental,
                f'{rental.vehicle.plate_number}, mulai sewa {_short_date(rental.start_at)}',
                'Periksa',
                change_url(rental),
            )
            for rental in drafts[:ATTENTION_LIMIT]
        ],
        'maintenance_count': maintenance_count,
        'outstanding_total': sum((rental.remaining_amount for rental in unpaid), Decimal('0')),
    }


def get_agenda(active_rentals, draft_rentals, now=None):
    """Pengambilan, pengembalian, dan perawatan dalam 7 hari ke depan."""
    now = now or timezone.now()
    today = timezone.localtime(now).date()
    day_start = timezone.make_aware(
        datetime.combine(today, datetime.min.time()), timezone.get_current_timezone(),
    )
    end = day_start + timedelta(days=AGENDA_DAYS + 1)
    items = []

    def add(moment, kind, text, url):
        local = timezone.localtime(moment)
        items.append({
            'sort': moment.timestamp(),
            'day': 'Hari ini' if local.date() == today else _short_date(moment),
            'is_today': local.date() == today,
            'time': f'{local:%H:%M}',
            'kind': kind,
            'text': text,
            'url': url,
        })

    for rental in active_rentals:
        url = reverse('admin:rentals_rental_change', args=[rental.pk])
        label = f'{rental.vehicle.plate_number} - {rental.customer.full_name}'
        if rental.expected_return_at and day_start <= rental.expected_return_at < end:
            add(rental.expected_return_at, 'Kembali', label, url)
        if rental.start_at and now < rental.start_at < end:
            add(rental.start_at, 'Ambil', label, url)

    for rental in draft_rentals:
        if rental.start_at and day_start <= rental.start_at < end:
            add(
                rental.start_at, 'Draf',
                f'{rental.vehicle.plate_number} - {rental.customer.full_name}',
                reverse('admin:rentals_rental_change', args=[rental.pk]),
            )

    maintenances = (
        VehicleMaintenance.objects.filter(
            status__in=[VehicleMaintenance.Status.PLANNED, VehicleMaintenance.Status.IN_PROGRESS],
            maintenance_date__gte=day_start,
            maintenance_date__lt=end,
        )
        .select_related('vehicle', 'category')
    )
    for maintenance in maintenances:
        add(
            maintenance.maintenance_date, 'Perawatan',
            f'{maintenance.vehicle.plate_number} - {maintenance.category}',
            reverse('admin:rentals_vehiclemaintenance_change', args=[maintenance.pk]),
        )

    items.sort(key=lambda item: item['sort'])
    return items[:AGENDA_LIMIT]


def get_money_series(year, month):
    """Pendapatan dan pengeluaran 6 bulan yang berakhir di bulan terpilih.

    Tiga query agregat per bulan (pembayaran, perawatan, biaya lain), bukan
    satu query per bulan.
    """
    months = [_shift_month(year, month, offset) for offset in range(-(CHART_MONTHS - 1), 1)]
    range_start, _ = month_bounds(*months[0])
    _, range_end = month_bounds(year, month)
    current_tz = timezone.get_current_timezone()

    def by_month(queryset, date_field, value_field):
        rows = (
            queryset.filter(**{f'{date_field}__gte': range_start, f'{date_field}__lt': range_end})
            .annotate(bucket=TruncMonth(date_field, tzinfo=current_tz))
            .values('bucket')
            .annotate(total=Sum(value_field))
            .order_by()
        )
        result = {}
        for row in rows:
            bucket = timezone.localtime(row['bucket'], current_tz)
            result[(bucket.year, bucket.month)] = row['total'] or Decimal('0')
        return result

    income = by_month(Payment.objects.all(), 'payment_date', 'amount')
    maintenance = by_month(
        VehicleMaintenance.objects.exclude(status=VehicleMaintenance.Status.CANCELLED),
        'maintenance_date', 'total_cost',
    )
    other = by_month(
        OtherExpense.objects.exclude(status=OtherExpense.Status.CANCELLED),
        'expense_date', 'total_cost',
    )

    return [
        {
            'year': y,
            'month': m,
            'label': MONTH_SHORT[m - 1],
            'full_label': format_period_label(y, m),
            'income': income.get((y, m), Decimal('0')),
            'expense': maintenance.get((y, m), Decimal('0')) + other.get((y, m), Decimal('0')),
        }
        for y, m in months
    ]


def build_chart(series):
    peak = max([max(row['income'], row['expense']) for row in series] + [Decimal('0')])

    def height(value):
        if not peak or value <= 0:
            return 0
        return max(2, round(float(value / peak) * 100))

    rows = []
    for index, row in enumerate(series):
        rows.append({
            'label': row['label'],
            'full_label': row['full_label'],
            'is_current': index == len(series) - 1,
            'income_height': height(row['income']),
            'expense_height': height(row['expense']),
            'income_text': format_rupiah(row['income']),
            'expense_text': format_rupiah(row['expense']),
            'income_short': format_rupiah_short(row['income']),
            'expense_short': format_rupiah_short(row['expense']),
        })
    return {'rows': rows, 'peak_text': format_rupiah_short(peak), 'has_data': bool(peak)}


def compare_with_previous(current, previous, previous_label, lower_is_better=False):
    if not previous:
        return {'text': f'Belum ada pembanding {previous_label}', 'tone': 'neutral'}
    change = (current - previous) / previous * 100
    rounded = int(change.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    if rounded == 0:
        return {'text': f'Sama dengan {previous_label}', 'tone': 'neutral'}
    good = (rounded < 0) if lower_is_better else (rounded > 0)
    arrow = 'naik' if rounded > 0 else 'turun'
    return {
        'text': f'{arrow.capitalize()} {abs(rounded)}% dibanding {previous_label}',
        'tone': 'good' if good else 'bad',
    }


def get_fleet(year, month, vehicle_total):
    """Utilisasi bulan terpilih dan daftar singkat kendaraan.

    Utilisasi = hari tersewa / (jumlah kendaraan x hari dalam bulan). Draf dan
    order dibatalkan tidak dihitung; hari yang sama pada satu unit dihitung sekali.
    """
    start, end = month_bounds(year, month)
    days_in_month = (end - start).days
    rentals = (
        Rental.objects.exclude(status__in=[Rental.Status.DRAFT, Rental.Status.CANCELLED])
        .filter(start_at__lt=end, expected_return_at__gte=start)
        .values_list('vehicle_id', 'start_at', 'expected_return_at', 'returned_at')
    )
    busy = set()
    month_start = timezone.localtime(start).date()
    month_end = timezone.localtime(end).date()
    for vehicle_id, start_at, expected_at, returned_at in rentals:
        first = max(timezone.localtime(start_at).date(), month_start)
        last_moment = returned_at or expected_at
        last = min(timezone.localtime(last_moment).date(), month_end - timedelta(days=1))
        day = first
        while day <= last:
            busy.add((vehicle_id, day))
            day += timedelta(days=1)

    capacity = vehicle_total * days_in_month
    utilization = round(len(busy) / capacity * 100) if capacity else 0

    status_labels = dict(Vehicle.Status.choices)
    vehicles = [
        {
            'name': f'{plate} - {brand} {model}',
            'status': status,
            'status_label': status_labels.get(status, status),
            'url': reverse('admin:rentals_vehicle_change', args=[pk]),
        }
        for pk, plate, brand, model, status in Vehicle.objects.order_by('plate_number')
        .values_list('pk', 'plate_number', 'brand', 'model', 'status')[:FLEET_LIMIT]
    ]
    return {'utilization': min(utilization, 100), 'vehicles': vehicles}


def get_dashboard_context(request):
    year, month = parse_dashboard_period(request)
    cache_seconds = getattr(settings, 'DASHBOARD_CACHE_SECONDS', 60)
    cache_key = f'rental-dashboard:{year:04d}-{month:02d}'

    if cache_seconds > 0:
        cached_context = safe_cache_get(cache_key)
        if cached_context is not None:
            return cached_context

    series = get_money_series(year, month)
    current, previous = series[-1], series[-2]
    monthly_income = current['income']
    monthly_expenses = current['expense']
    net_profit = monthly_income - monthly_expenses

    # Satu query untuk tiga angka, bukan tiga COUNT terpisah.
    vehicle_stats = Vehicle.objects.aggregate(
        total=Count('pk'),
        available=Count('pk', filter=Q(status=Vehicle.Status.AVAILABLE)),
        rented=Count('pk', filter=Q(status=Vehicle.Status.RENTED)),
        maintenance=Count('pk', filter=Q(status=Vehicle.Status.MAINTENANCE)),
    )

    active_rentals = get_active_rentals()
    draft_rentals = get_draft_rentals()
    attention = get_attention_items(
        vehicle_stats['maintenance'] or 0,
        active_rentals=active_rentals,
        draft_rentals=draft_rentals,
    )

    context = {
        'total_vehicles': vehicle_stats['total'] or 0,
        'available_vehicles': vehicle_stats['available'] or 0,
        'rented_vehicles': vehicle_stats['rented'] or 0,
        'maintenance_vehicles': vehicle_stats['maintenance'] or 0,
        'monthly_income': format_rupiah_short(monthly_income),
        'monthly_income_full': format_rupiah(monthly_income),
        'monthly_expenses': format_rupiah_short(monthly_expenses),
        'monthly_expenses_full': format_rupiah(monthly_expenses),
        'income_change': compare_with_previous(monthly_income, previous['income'], previous['full_label']),
        'expense_change': compare_with_previous(
            monthly_expenses, previous['expense'], previous['full_label'], lower_is_better=True,
        ),
        'net_profit_full': format_rupiah(net_profit),
        'net_profit_negative': net_profit < 0,
        'outstanding_full': format_rupiah(attention['outstanding_total']),
        'outstanding_count': attention['unpaid_count'],
        'chart': build_chart(series),
        'fleet': get_fleet(year, month, vehicle_stats['total'] or 0),
        'agenda': get_agenda(active_rentals, draft_rentals),
        'attention': attention,
        'selected_period': f'{year:04d}-{month:02d}',
        'selected_period_label': format_period_label(year, month),
    }

    if cache_seconds > 0:
        safe_cache_set(cache_key, context, cache_seconds)

    return context
