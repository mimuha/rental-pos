import json
from datetime import date, datetime, time, timedelta

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
    'available': '#16a34a',
    'rented': '#2563eb',
    'maintenance': '#dc2626',
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


def _exclusive_end_date(value):
    return _local_date(value) + timedelta(days=1)


def _date_range(start_date, end_date):
    current = start_date
    while current < end_date:
        yield current
        current += timedelta(days=1)


def booking_calendar(request):
    context = admin.site.each_context(request)
    context.update({
        'title': 'Kalender Booking',
        'vehicles': Vehicle.objects.order_by('plate_number'),
        'status_options': (
            ('', 'Semua status'),
            ('available', 'Tersedia'),
            ('rented', 'Sedang dirental'),
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

    vehicle_qs = Vehicle.objects.order_by('plate_number')
    if vehicle_id:
        vehicle_qs = vehicle_qs.filter(pk=vehicle_id)
    vehicle_ids = list(vehicle_qs.values_list('pk', flat=True))

    events = []
    busy_dates_by_vehicle = {pk: set() for pk in vehicle_ids}

    rentals = Rental.objects.select_related('vehicle', 'customer').filter(
        vehicle_id__in=vehicle_ids,
        start_at__date__lt=end_date,
        expected_return_at__date__gte=start_date,
    ).exclude(status=Rental.Status.CANCELLED)

    if status in ('', 'rented'):
        for rental in rentals:
            rental_start = max(_local_date(rental.start_at), start_date)
            rental_end = min(_exclusive_end_date(rental.expected_return_at), end_date)
            busy_dates_by_vehicle.setdefault(rental.vehicle_id, set()).update(_date_range(rental_start, rental_end))
            events.append({
                'id': f'rental-{rental.pk}',
                'title': f'{rental.vehicle.plate_number}\n{rental.customer.full_name}',
                'start': rental_start.isoformat(),
                'end': rental_end.isoformat(),
                'allDay': True,
                'editable': True,
                'backgroundColor': BOOKING_STATUS_COLORS['rented'],
                'borderColor': BOOKING_STATUS_COLORS['rented'],
                'url': reverse('admin:rentals_rental_change', args=[rental.pk]),
                'extendedProps': {
                    'type': 'rental',
                    'plate_number': rental.vehicle.plate_number,
                    'customer_name': rental.customer.full_name,
                    'status_label': rental.get_status_display(),
                },
            })
    else:
        for rental in rentals:
            rental_start = max(_local_date(rental.start_at), start_date)
            rental_end = min(_exclusive_end_date(rental.expected_return_at), end_date)
            busy_dates_by_vehicle.setdefault(rental.vehicle_id, set()).update(_date_range(rental_start, rental_end))

    maintenances = VehicleMaintenance.objects.select_related('vehicle').filter(
        vehicle_id__in=vehicle_ids,
        maintenance_date__date__gte=start_date,
        maintenance_date__date__lt=end_date,
    ).exclude(status=VehicleMaintenance.Status.CANCELLED)

    if status in ('', 'maintenance'):
        for maintenance in maintenances:
            maintenance_start = _local_date(maintenance.maintenance_date)
            maintenance_end = maintenance_start + timedelta(days=1)
            busy_dates_by_vehicle.setdefault(maintenance.vehicle_id, set()).add(maintenance_start)
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
    else:
        for maintenance in maintenances:
            busy_dates_by_vehicle.setdefault(maintenance.vehicle_id, set()).add(_local_date(maintenance.maintenance_date))

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
    if not event_id.startswith('rental-'):
        return JsonResponse({'ok': False, 'error': 'Hanya booking rental yang dapat di-reschedule.'}, status=400)

    rental = get_object_or_404(Rental, pk=event_id.replace('rental-', '', 1))
    new_start_date = _parse_date(payload.get('start'), None)
    if new_start_date is None:
        return JsonResponse({'ok': False, 'error': 'Tanggal mulai tidak valid.'}, status=400)

    original_start = timezone.localtime(rental.start_at) if timezone.is_aware(rental.start_at) else rental.start_at
    original_end = timezone.localtime(rental.expected_return_at) if timezone.is_aware(rental.expected_return_at) else rental.expected_return_at
    duration = original_end - original_start
    new_start = datetime.combine(new_start_date, original_start.time() or time(hour=9))
    if timezone.is_naive(new_start):
        new_start = timezone.make_aware(new_start, timezone.get_current_timezone())

    rental.start_at = new_start
    rental.expected_return_at = new_start + duration

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
