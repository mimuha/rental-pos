from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.urls import reverse
from django.utils import timezone

from .models import OtherExpense, Payment, Vehicle, VehicleMaintenance


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


def sum_monthly_expenses(year, month):
    start, end = month_bounds(year, month)

    maintenance_total = VehicleMaintenance.objects.filter(
        maintenance_date__gte=start,
        maintenance_date__lt=end,
    ).exclude(
        status=VehicleMaintenance.Status.CANCELLED,
    ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0')

    other_expense_total = OtherExpense.objects.filter(
        expense_date__gte=start,
        expense_date__lt=end,
    ).exclude(
        status=OtherExpense.Status.CANCELLED,
    ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0')

    return maintenance_total + other_expense_total

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


def get_dashboard_context(request):
    year, month = parse_dashboard_period(request)
    cache_seconds = getattr(settings, 'DASHBOARD_CACHE_SECONDS', 60)
    cache_key = f'rental-dashboard:{year:04d}-{month:02d}'

    if cache_seconds > 0:
        cached_context = cache.get(cache_key)
        if cached_context is not None:
            return cached_context

    start, end = month_bounds(year, month)

    monthly_income = Payment.objects.filter(
        payment_date__gte=start,
        payment_date__lt=end,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    monthly_expenses = sum_monthly_expenses(year, month)

    # Satu query untuk tiga angka, bukan tiga COUNT terpisah.
    vehicle_stats = Vehicle.objects.aggregate(
        total=Count('pk'),
        available=Count('pk', filter=Q(status=Vehicle.Status.AVAILABLE)),
        rented=Count('pk', filter=Q(status=Vehicle.Status.RENTED)),
    )

    context = {
        'total_vehicles': vehicle_stats['total'] or 0,
        'available_vehicles': vehicle_stats['available'] or 0,
        'rented_vehicles': vehicle_stats['rented'] or 0,
        'monthly_income': format_rupiah_short(monthly_income),
        'monthly_expenses': format_rupiah_short(monthly_expenses),
        'selected_period': f'{year:04d}-{month:02d}',
        'selected_period_label': format_period_label(year, month),
    }

    if cache_seconds > 0:
        cache.set(cache_key, context, cache_seconds)

    return context
