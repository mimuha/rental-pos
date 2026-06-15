from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from .models import OtherExpense, Payment, Vehicle, VehicleMaintenance


def sum_monthly_expenses(year, month):
    maintenance_total = VehicleMaintenance.objects.filter(
        maintenance_date__year=year,
        maintenance_date__month=month,
    ).exclude(
        status=VehicleMaintenance.Status.CANCELLED,
    ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0')

    other_expense_total = OtherExpense.objects.filter(
        expense_date__year=year,
        expense_date__month=month,
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


def group_rental_menu(models):
    models_by_name = {
        model['object_name'].lower(): model
        for model in models
    }
    if 'financialreport' not in models_by_name:
        models_by_name['financialreport'] = financial_report_menu_model()

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

    monthly_income = Payment.objects.filter(
        payment_date__year=year,
        payment_date__month=month,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    monthly_expenses = sum_monthly_expenses(year, month)

    return {
        'total_vehicles': Vehicle.objects.count(),
        'available_vehicles': Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE).count(),
        'rented_vehicles': Vehicle.objects.filter(status=Vehicle.Status.RENTED).count(),
        'monthly_income': format_rupiah_short(monthly_income),
        'monthly_expenses': format_rupiah_short(monthly_expenses),
        'selected_period': f'{year:04d}-{month:02d}',
        'selected_period_label': format_period_label(year, month),
    }
