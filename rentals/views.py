import json
import re
from datetime import date, datetime, time as dt_time, timedelta
from datetime import timezone as dt_timezone

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Rental, Vehicle, VehicleMaintenance


BOOKING_STATUS_COLORS = {
    'available': 'var(--rental-calendar-available)',
    'rented': 'var(--rental-calendar-rented)',
    'draft': 'var(--rental-calendar-draft)',
    'maintenance': 'var(--rental-calendar-maintenance)',
}


def _parse_date(value, default):
    if not value:
        return default
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return default


def _local_date(value):
    if timezone.is_aware(value):
        return timezone.localtime(value).date()
    return value.date()


def _aware_midnight(day):
    """Awal hari (00:00) di timezone aktif, untuk filter rentang datetime.

    Lookup `__date` membuat Postgres menghitung konversi tanggal per baris
    sehingga index pada kolom datetime tidak terpakai.
    """
    return timezone.make_aware(
        datetime.combine(day, dt_time.min),
        timezone.get_current_timezone(),
    )


def _exclusive_end_date(value):
    return _local_date(value) + timedelta(days=1)


def _date_range(start_date, end_date):
    current = start_date
    while current < end_date:
        yield current
        current += timedelta(days=1)


def _localize_wall_time(naive_value, tz):
    candidate = naive_value.replace(tzinfo=tz)
    if candidate.astimezone(dt_timezone.utc).astimezone(tz).replace(tzinfo=None) == naive_value:
        return candidate

    for minutes in range(1, 181):
        shifted = naive_value + timedelta(minutes=minutes)
        candidate = shifted.replace(tzinfo=tz)
        if candidate.astimezone(dt_timezone.utc).astimezone(tz).replace(tzinfo=None) == shifted:
            return candidate

    return naive_value.replace(tzinfo=tz)


def booking_calendar(request):
    context = admin.site.each_context(request)
    context.update({
        'title': 'Kalender Booking',
        'vehicles': Vehicle.objects.order_by('plate_number'),
        'status_options': (
            ('', 'Semua status'),
            ('available', 'Tersedia'),
            ('rented', 'Sedang dirental'),
            ('draft', 'Draf'),
            ('maintenance', 'Maintenance'),
        ),
        'events_url': reverse('admin:rental_booking_calendar_events'),
        'reschedule_url': reverse('admin:rental_booking_calendar_reschedule'),
        'rental_add_url': reverse('admin:rentals_rental_add'),
    })
    return TemplateResponse(request, 'admin/kalender_booking.html', context)


def booking_calendar_events(request):
    start_date = _parse_date(request.GET.get('start'), timezone.localdate().replace(day=1))
    end_date = _parse_date(request.GET.get('end'), start_date + timedelta(days=42))
    vehicle_id = request.GET.get('vehicle') or ''
    status = request.GET.get('status') or ''

    vehicle_qs = Vehicle.objects.order_by('plate_number').only(
        'pk', 'plate_number', 'status',
    )
    if vehicle_id:
        vehicle_qs = vehicle_qs.filter(pk=vehicle_id)
    vehicle_ids = list(vehicle_qs.values_list('pk', flat=True))

    range_start = _aware_midnight(start_date)
    range_end = _aware_midnight(end_date)

    events = []
    busy_dates_by_vehicle = {pk: set() for pk in vehicle_ids}

    rentals = list(
        Rental.objects.select_related('vehicle', 'customer').filter(
            vehicle_id__in=vehicle_ids,
            start_at__lt=range_end,
            expected_return_at__gte=range_start,
        ).exclude(status=Rental.Status.CANCELLED)
    )
    confirmed_rentals = [
        rental for rental in rentals if rental.status != Rental.Status.DRAFT
    ]

    for rental in confirmed_rentals:
        rental_start = max(_local_date(rental.start_at), start_date)
        rental_end = min(_exclusive_end_date(rental.expected_return_at), end_date)
        busy_dates_by_vehicle.setdefault(rental.vehicle_id, set()).update(_date_range(rental_start, rental_end))

    if status in ('', 'rented', 'draft'):
        if status == 'rented':
            display_rentals = confirmed_rentals
        elif status == 'draft':
            display_rentals = [
                rental for rental in rentals if rental.status == Rental.Status.DRAFT
            ]
        else:
            display_rentals = rentals

        for rental in display_rentals:
            is_draft = rental.status == Rental.Status.DRAFT
            color = BOOKING_STATUS_COLORS['draft' if is_draft else 'rented']
            rental_start = max(_local_date(rental.start_at), start_date)
            rental_end = min(_exclusive_end_date(rental.expected_return_at), end_date)
            events.append({
                'id': f'rental-{rental.pk}',
                'title': f'{rental.vehicle.plate_number}\n{rental.customer.full_name}',
                'start': rental_start.isoformat(),
                'end': rental_end.isoformat(),
                'allDay': True,
                'editable': True,
                'backgroundColor': color,
                'borderColor': color,
                'url': reverse('admin:rentals_rental_change', args=[rental.pk]),
                'extendedProps': {
                    'type': 'rental',
                    'plate_number': rental.vehicle.plate_number,
                    'customer_name': rental.customer.full_name,
                    'status_label': rental.get_status_display(),
                },
            })

    maintenances = list(
        VehicleMaintenance.objects.select_related('vehicle').filter(
            vehicle_id__in=vehicle_ids,
            maintenance_date__gte=range_start,
            maintenance_date__lt=range_end,
        ).exclude(status=VehicleMaintenance.Status.CANCELLED)
    )

    for maintenance in maintenances:
        busy_dates_by_vehicle.setdefault(maintenance.vehicle_id, set()).add(
            _local_date(maintenance.maintenance_date)
        )

    if status in ('', 'maintenance'):
        for maintenance in maintenances:
            maintenance_start = _local_date(maintenance.maintenance_date)
            maintenance_end = maintenance_start + timedelta(days=1)
            events.append({
                'id': f'maintenance-{maintenance.pk}',
                'title': f'{maintenance.vehicle.plate_number}\nMaintenance',
                'start': maintenance_start.isoformat(),
                'end': maintenance_end.isoformat(),
                'allDay': True,
                'editable': False,
                'backgroundColor': BOOKING_STATUS_COLORS['maintenance'],
                'borderColor': BOOKING_STATUS_COLORS['maintenance'],
                'url': reverse('admin:rentals_vehiclemaintenance_change', args=[maintenance.pk]),
                'extendedProps': {
                    'type': 'maintenance',
                    'plate_number': maintenance.vehicle.plate_number,
                    'customer_name': 'Maintenance',
                    'status_label': maintenance.get_status_display(),
                },
            })

    if status in ('', 'available'):
        available_vehicles = vehicle_qs.filter(status=Vehicle.Status.AVAILABLE)
        for vehicle in available_vehicles:
            busy_dates = busy_dates_by_vehicle.get(vehicle.pk, set())
            for current_date in _date_range(start_date, end_date):
                if current_date in busy_dates:
                    continue
                events.append({
                    'id': f'available-{vehicle.pk}-{current_date.isoformat()}',
                    'title': f'{vehicle.plate_number}\nTersedia',
                    'start': current_date.isoformat(),
                    'end': (current_date + timedelta(days=1)).isoformat(),
                    'allDay': True,
                    'editable': False,
                    'backgroundColor': BOOKING_STATUS_COLORS['available'],
                    'borderColor': BOOKING_STATUS_COLORS['available'],
                    'extendedProps': {
                        'type': 'available',
                        'vehicle_id': vehicle.pk,
                        'plate_number': vehicle.plate_number,
                        'customer_name': 'Tersedia',
                        'status_label': vehicle.get_status_display(),
                    },
                })

    return JsonResponse(events, safe=False)


@require_POST
def booking_calendar_reschedule(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'Payload tidak valid.'}, status=400)

    event_id = str(payload.get('event_id', ''))
    match = re.fullmatch(r'rental-(\d+)', event_id)
    if not match:
        return JsonResponse({'ok': False, 'error': 'ID booking tidak valid.'}, status=400)

    rental = get_object_or_404(Rental, pk=int(match.group(1)))
    if rental.status == Rental.Status.CANCELLED:
        return JsonResponse({'ok': False, 'error': 'Booking yang dibatalkan tidak dapat di-reschedule.'}, status=400)
    new_start_date = _parse_date(payload.get('start'), None)
    if new_start_date is None:
        return JsonResponse({'ok': False, 'error': 'Tanggal mulai tidak valid.'}, status=400)

    current_tz = timezone.get_current_timezone()
    original_start = rental.start_at
    original_end = rental.expected_return_at
    if timezone.is_naive(original_start):
        original_start = timezone.make_aware(original_start, current_tz)
    if timezone.is_naive(original_end):
        original_end = timezone.make_aware(original_end, current_tz)

    duration = (
        original_end.astimezone(dt_timezone.utc)
        - original_start.astimezone(dt_timezone.utc)
    )
    time_of_day = original_start.astimezone(current_tz).timetz().replace(tzinfo=None)
    new_start = _localize_wall_time(
        datetime.combine(new_start_date, time_of_day),
        current_tz,
    )
    new_end = (
        new_start.astimezone(dt_timezone.utc) + duration
    ).astimezone(current_tz)

    rental.start_at = new_start
    rental.expected_return_at = new_end

    try:
        rental.save(update_fields=['start_at', 'expected_return_at', 'updated_at'])
    except ValidationError as exc:
        message = '; '.join(
            item
            for messages in exc.message_dict.values()
            for item in messages
        ) if hasattr(exc, 'message_dict') else '; '.join(exc.messages)
        return JsonResponse({'ok': False, 'error': message}, status=400)

    return JsonResponse({
        'ok': True,
        'start': _local_date(rental.start_at).isoformat(),
        'end': _exclusive_end_date(rental.expected_return_at).isoformat(),
    })
