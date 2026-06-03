from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST
from decimal import Decimal
from django.db.models import Sum, Q
from datetime import datetime, timedelta, date
from django.urls import reverse
from django.utils.html import format_html
import csv
from django.utils import timezone
from django.utils.encoding import smart_str

from .dashboard import apply_rental_menu_groups, get_dashboard_context
from .models import (
    Customer,
    ExpenseType,
    MaintenanceCategory,
    MaintenanceVendor,
    OtherExpense,
    Payment,
    Rental,
    Vehicle,
    VehicleCategory,
    VehicleMaintenance,
    VehiclePhoto,
)
from .views import booking_calendar, booking_calendar_events, booking_calendar_reschedule
from .forms import VehiclePhotoForm, upload_to_supabase, MAX_FILE_SIZE


admin.site.site_header = 'Admin POS Rental Mobil'
admin.site.site_title = 'POS Rental Mobil'
admin.site.index_title = 'Manajemen Rental Mobil'


def format_rupiah(value):
    if value is None:
        return '-'

    amount = f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    return f'Rp{amount}'


def export_selected_to_csv(modeladmin, request, queryset):
    """Admin action: export selected objects to CSV and return as download."""
    opts = modeladmin.model._meta
    now = timezone.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{opts.app_label}_{opts.model_name}_{now}.csv"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Use model fields for CSV columns
    fields = [f for f in modeladmin.model._meta.fields]
    header = [smart_str(f.verbose_name) for f in fields]
    writer.writerow(header)

    for obj in queryset:
        row = []
        for f in fields:
            try:
                val = getattr(obj, f.name)
            except Exception:
                val = ''
            # callables
            if callable(val):
                try:
                    val = val()
                except Exception:
                    val = str(val)
            row.append(smart_str(val))
        writer.writerow(row)

    return response


class BaseModelAdmin(admin.ModelAdmin):
    """
    Base ModelAdmin that replaces the default empty choice label ("---------")
    with a localized label ('pilih..') and ensures choice fields include that
    label when blank. This applies across the admin when other ModelAdmin
    classes inherit from this base.
    """
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if 'empty_label' not in kwargs:
            kwargs['empty_label'] = 'pilih..'
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        form_field = super().formfield_for_choice_field(db_field, request, **kwargs)
        if form_field is None:
            return form_field

        # Ensure choices is a mutable list so we can modify the empty label.
        choices = list(form_field.choices)
        if choices:
            # If the first choice is the empty value, replace its label.
            if choices[0][0] == '':
                choices[0] = ('', 'pilih..')
            else:
                # If no empty choice exists but the model field allows blank,
                # insert an empty choice at the front.
                if getattr(db_field, 'blank', False):
                    choices.insert(0, ('', 'pilih..'))

        form_field.choices = choices
        return form_field


@admin.register(Customer)
class CustomerAdmin(BaseModelAdmin):
    list_display = ['full_name', 'identity_number', 'phone_number', 'email']
    search_fields = ['full_name', 'identity_number', 'phone_number', 'email']
    list_per_page = 25


@admin.register(VehicleCategory)
class VehicleCategoryAdmin(BaseModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


class VehiclePhotoInline(admin.TabularInline):
    model = VehiclePhoto
    template = "admin/edit_inline/tabular_vehicle_photos.html"
    extra = 0
    max_num = 5
    can_delete = False
    fields = []
    verbose_name = 'Foto kendaraan'
    verbose_name_plural = 'Foto kendaraan (maks. 5, @max 1MB)'
    readonly_fields = []

    class Media:
        css = {"all": ("admin/css/vehicle_photos_inline.css",)}
        js = ("admin/js/vehicle_photos_inline.js",)

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('order')

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return True


@admin.register(Vehicle)
class VehicleAdmin(BaseModelAdmin):
    list_display = [
        'plate_number',
        'brand',
        'model',
        'category',
        'year',
        'status',
        'daily_rate_rupiah',
    ]
    list_filter = ['status', 'category', 'transmission', 'fuel_type']
    search_fields = ['plate_number', 'brand', 'model']
    list_per_page = 25
    inlines = [VehiclePhotoInline]

    @admin.display(description='Tarif harian')
    def daily_rate_rupiah(self, obj):
        return format_rupiah(obj.daily_rate)


@admin.register(MaintenanceCategory)
class MaintenanceCategoryAdmin(BaseModelAdmin):
    list_display = ['name', 'category_type', 'description']
    list_filter = ['category_type']
    search_fields = ['name', 'description']
    list_per_page = 25


@admin.register(MaintenanceVendor)
class MaintenanceVendorAdmin(BaseModelAdmin):
    list_display = ['name', 'contact_person', 'phone_number']
    search_fields = ['name', 'contact_person', 'phone_number', 'address']
    list_per_page = 25


@admin.register(VehicleMaintenance)
class VehicleMaintenanceAdmin(BaseModelAdmin):
    list_display = [
        'maintenance_date',
        'vehicle',
        'category',
        'vendor',
        'status_badge',
        'total_cost_rupiah',
    ]
    list_filter = ['status', 'category', 'vendor', 'maintenance_date']
    search_fields = [
        'vehicle__plate_number',
        'vehicle__brand',
        'vehicle__model',
        'category__name',
        'vendor__name',
        'issue_description',
        'parts_replaced',
    ]
    readonly_fields = ['total_cost_rupiah']
    date_hierarchy = 'maintenance_date'
    list_per_page = 25

    fieldsets = (
        ('Informasi maintenance', {
            'fields': ('vehicle', 'category', 'vendor', 'maintenance_date', 'status'),
        }),
        ('Detail pekerjaan', {
            'fields': ('odometer', 'issue_description', 'parts_replaced', 'notes'),
        }),
        ('Biaya', {
            'fields': ('total_cost', 'total_cost_rupiah'),
        }),
    )

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            VehicleMaintenance.Status.PLANNED: '#6b7280',
            VehicleMaintenance.Status.IN_PROGRESS: '#6d4be8',
            VehicleMaintenance.Status.COMPLETED: '#5638c9',
            VehicleMaintenance.Status.CANCELLED: '#dc2626',
        }
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}</span>',
            colors.get(obj.status, '#111827'),
            obj.get_status_display(),
        )

    @admin.display(description='Biaya')
    def total_cost_rupiah(self, obj):
        if obj is None:
            return '-'
        return format_rupiah(obj.total_cost)


@admin.register(ExpenseType)
class ExpenseTypeAdmin(BaseModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name', 'description']
    list_per_page = 25


@admin.register(OtherExpense)
class OtherExpenseAdmin(BaseModelAdmin):
    list_display = [
        'expense_date',
        'expense_type',
        'payee',
        'status_badge',
        'total_cost_rupiah',
    ]
    list_filter = ['status', 'expense_type', 'expense_date']
    search_fields = [
        'expense_type__name',
        'payee',
        'description',
        'reference_number',
        'notes',
    ]
    readonly_fields = ['total_cost_rupiah']
    date_hierarchy = 'expense_date'
    list_per_page = 25

    fieldsets = (
        ('Informasi biaya', {
            'fields': ('expense_type', 'expense_date', 'status', 'payee', 'reference_number'),
        }),
        ('Detail', {
            'fields': ('description', 'notes'),
        }),
        ('Nominal', {
            'fields': ('total_cost', 'total_cost_rupiah'),
        }),
    )

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            OtherExpense.Status.PLANNED: '#6b7280',
            OtherExpense.Status.IN_PROGRESS: '#6d4be8',
            OtherExpense.Status.COMPLETED: '#5638c9',
            OtherExpense.Status.CANCELLED: '#dc2626',
        }
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}</span>',
            colors.get(obj.status, '#111827'),
            obj.get_status_display(),
        )

    @admin.display(description='Biaya')
    def total_cost_rupiah(self, obj):
        if obj is None:
            return '-'
        return format_rupiah(obj.total_cost)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ['payment_date', 'method', 'amount', 'reference_number', 'notes']
    verbose_name = 'Pembayaran'
    verbose_name_plural = 'Pembayaran'


@admin.register(Rental)
class RentalAdmin(BaseModelAdmin):
    list_display = [
        'invoice_number',
        'customer',
        'vehicle',
        'start_at',
        'expected_return_at',
        'status_badge',
        'total_amount_rupiah',
        'remaining_amount_rupiah',
    ]
    list_filter = ['status', 'start_at', 'expected_return_at']
    search_fields = ['invoice_number', 'customer__full_name', 'vehicle__plate_number']
    readonly_fields = [
        'invoice_number',
        'status_badge',
        'subtotal_rupiah',
        'total_amount_rupiah',
        'paid_amount_rupiah',
        'remaining_amount_rupiah',
    ]
    inlines = [PaymentInline]
    date_hierarchy = 'start_at'
    list_per_page = 25

    fieldsets = (
        ('Informasi transaksi', {
            'fields': ('invoice_number', 'customer', 'vehicle', 'status_badge', 'notes'),
        }),
        ('Jadwal dan odometer', {
            'fields': ('start_at', 'expected_return_at', 'returned_at', 'start_odometer', 'end_odometer'),
        }),
        ('Nominal Rupiah', {
            'fields': (
                'daily_rate',
                'discount_amount',
                'additional_fee',
                'deposit_amount',
                'subtotal_rupiah',
                'total_amount_rupiah',
                'paid_amount_rupiah',
                'remaining_amount_rupiah',
            ),
        }),
    )

    @admin.display(description='Status')
    def status_badge(self, obj):
        if obj is None:
            return format_html(
                '<span style="color: #6b7280; font-weight: 600;">{}</span>',
                Rental.Status.DRAFT.label,
            )

        colors = {
            Rental.Status.DRAFT: '#6b7280',
            Rental.Status.ACTIVE: '#6d4be8',
            Rental.Status.COMPLETED: '#5638c9',
            Rental.Status.CANCELLED: '#dc2626',
        }
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}</span>',
            colors.get(obj.status, '#111827'),
            obj.get_status_display(),
        )

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        for field_name in ('start_at', 'expected_return_at'):
            raw_value = request.GET.get(field_name)
            if not raw_value:
                continue

            try:
                parsed_value = datetime.fromisoformat(raw_value)
            except ValueError:
                continue

            if timezone.is_naive(parsed_value):
                parsed_value = timezone.make_aware(parsed_value, timezone.get_current_timezone())
            initial[field_name] = parsed_value

        return initial

    def response_change(self, request, obj):
        if '_activate_rental' in request.POST:
            if obj.status == Rental.Status.DRAFT:
                obj.status = Rental.Status.ACTIVE
                obj.save(update_fields=['status', 'updated_at'])
                self.message_user(request, f'Transaksi {obj.invoice_number} berhasil diaktifkan.')
            else:
                self.message_user(request, 'Hanya transaksi berstatus draf yang dapat diaktifkan.', level='warning')
            return HttpResponseRedirect(request.path)

        if '_complete_rental' in request.POST:
            if obj.status == Rental.Status.ACTIVE:
                obj.status = Rental.Status.COMPLETED
                obj.save(update_fields=['status', 'updated_at'])
                self.message_user(request, f'Transaksi {obj.invoice_number} berhasil diselesaikan.')
            else:
                self.message_user(request, 'Hanya transaksi berstatus aktif yang dapat diselesaikan.', level='warning')
            return HttpResponseRedirect(request.path)

        return super().response_change(request, obj)

    @admin.display(description='Subtotal')
    def subtotal_rupiah(self, obj):
        if obj is None:
            return '-'
        return format_rupiah(obj.subtotal)

    @admin.display(description='Total')
    def total_amount_rupiah(self, obj):
        if obj is None:
            return '-'
        return format_rupiah(obj.total_amount)

    @admin.display(description='Sudah dibayar')
    def paid_amount_rupiah(self, obj):
        if obj is None:
            return '-'
        return format_rupiah(obj.paid_amount)

    @admin.display(description='Sisa pembayaran')
    def remaining_amount_rupiah(self, obj):
        if obj is None:
            return '-'
        return format_rupiah(obj.remaining_amount)


@admin.register(Payment)
class PaymentAdmin(BaseModelAdmin):
    list_display = ['rental', 'payment_date', 'method', 'amount_rupiah', 'reference_number']
    list_filter = ['method', 'payment_date']
    search_fields = ['rental__invoice_number', 'reference_number']
    date_hierarchy = 'payment_date'

    @admin.display(description='Jumlah pembayaran')
    def amount_rupiah(self, obj):
        return format_rupiah(obj.amount)


_original_admin_index = admin.site.index
_original_admin_app_index = admin.site.app_index
_original_each_context = admin.site.each_context


def rental_each_context(request):
    context = _original_each_context(request)
    if 'available_apps' in context:
        apply_rental_menu_groups(context['available_apps'])
    return context


def rental_admin_index(request, extra_context=None):
    context = dict(extra_context or {})
    context.update(get_dashboard_context(request))
    response = _original_admin_index(request, context)
    if hasattr(response, 'context_data') and response.context_data is not None:
        apply_rental_menu_groups(response.context_data.get('app_list', []))
        apply_rental_menu_groups(response.context_data.get('available_apps', []))
    return response


def rental_admin_app_index(request, app_label, extra_context=None):
    # Redirect certain app index pages back to the admin home
    if app_label in ('rentals', 'auth'):
        url = reverse('admin:index')
        query = request.GET.urlencode()
        if query:
            url = f'{url}?{query}'
        return redirect(url)
    return _original_admin_app_index(request, app_label, extra_context)


admin.site.each_context = rental_each_context
admin.site.index = rental_admin_index
admin.site.app_index = rental_admin_app_index

# Register global admin action for exporting selected items to CSV
try:
    admin.site.add_action(export_selected_to_csv, name='export_selected_to_csv')
except Exception:
    # ignore if already registered or running in environments where add_action isn't available
    pass


# -- Financial report views & urls -------------------------------------------------
def parse_date_range(request):
    start_str = request.GET.get('start_date', '').strip()
    end_str = request.GET.get('end_date', '').strip()
    today = timezone.localtime().date()
    default_start = today.replace(day=1)
    # calculate last day of month
    next_month = (default_start.replace(day=28) + timedelta(days=4))
    default_end = next_month - timedelta(days=next_month.day)

    try:
        start = date.fromisoformat(start_str) if start_str else default_start
    except Exception:
        start = default_start
    try:
        end = date.fromisoformat(end_str) if end_str else default_end
    except Exception:
        end = default_end
    return start, end


def financial_report(request):
    start_date, end_date = parse_date_range(request)

    payments_qs = Payment.objects.filter(payment_date__date__gte=start_date, payment_date__date__lte=end_date)
    payments_total = payments_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    other_qs = OtherExpense.objects.filter(expense_date__date__gte=start_date, expense_date__date__lte=end_date).exclude(status=OtherExpense.Status.CANCELLED)
    other_total = other_qs.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')

    maintenance_qs = VehicleMaintenance.objects.filter(maintenance_date__date__gte=start_date, maintenance_date__date__lte=end_date).exclude(status=VehicleMaintenance.Status.CANCELLED)
    maintenance_total = maintenance_qs.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')

    rentals_qs = Rental.objects.filter(start_at__date__gte=start_date, start_at__date__lte=end_date).exclude(status=Rental.Status.CANCELLED)
    rentals_total = sum((r.total_amount or Decimal('0') for r in rentals_qs), Decimal('0'))

    income_total = payments_total
    expenses_total = other_total + maintenance_total
    profit = income_total - expenses_total

    payments = list(payments_qs.order_by('payment_date'))
    other_expenses = list(other_qs.order_by('expense_date'))
    maintenances = list(maintenance_qs.order_by('maintenance_date'))
    rentals = list(rentals_qs.order_by('start_at'))

    # Create lightweight display objects with rupiah-formatted fields for template.
    payments_display = [
        {
            **{'obj': p},
            'amount_fmt': format_rupiah(getattr(p, 'amount', None)),
        }
        for p in payments
    ]
    other_expenses_display = [
        {
            **{'obj': o},
            'total_cost_fmt': format_rupiah(getattr(o, 'total_cost', None)),
        }
        for o in other_expenses
    ]
    maintenances_display = [
        {
            **{'obj': m},
            'total_cost_fmt': format_rupiah(getattr(m, 'total_cost', None)),
        }
        for m in maintenances
    ]

    context = admin.site.each_context(request)
    context.update({
        'title': 'Laporan Keuangan',
        'start_date': start_date,
        'end_date': end_date,
        'payments_total': payments_total,
        'other_total': other_total,
        'maintenance_total': maintenance_total,
        'rentals_total': rentals_total,
        'income_total': income_total,
        'expenses_total': expenses_total,
        'profit': profit,
        'payments_total_fmt': format_rupiah(payments_total),
        'other_total_fmt': format_rupiah(other_total),
        'maintenance_total_fmt': format_rupiah(maintenance_total),
        'rentals_total_fmt': format_rupiah(rentals_total),
        'income_total_fmt': format_rupiah(income_total),
        'expenses_total_fmt': format_rupiah(expenses_total),
        'profit_fmt': format_rupiah(profit),
        'payments_display': payments_display,
        'other_expenses_display': other_expenses_display,
        'maintenances_display': maintenances_display,
        # keep original querysets for potential other uses
        'payments': payments,
        'other_expenses': other_expenses,
        'maintenances': maintenances,
        'rentals': rentals,
    })
    return TemplateResponse(request, 'admin/financial_report.html', context)


def financial_report_csv(request):
    start_date, end_date = parse_date_range(request)

    payments_qs = Payment.objects.filter(payment_date__date__gte=start_date, payment_date__date__lte=end_date)
    other_qs = OtherExpense.objects.filter(expense_date__date__gte=start_date, expense_date__date__lte=end_date).exclude(status=OtherExpense.Status.CANCELLED)
    maintenance_qs = VehicleMaintenance.objects.filter(maintenance_date__date__gte=start_date, maintenance_date__date__lte=end_date).exclude(status=VehicleMaintenance.Status.CANCELLED)
    rentals_qs = Rental.objects.filter(start_at__date__gte=start_date, start_at__date__lte=end_date).exclude(status=Rental.Status.CANCELLED)

    now = timezone.now().strftime("%Y%m%d_%H%M%S")
    filename = f"financial_report_{start_date}_{end_date}_{now}.csv"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)

    writer.writerow([
        'Tipe',
        'Tanggal',
        'Referensi',
        'Deskripsi',
        'Kredit',
        'Debit'
    ])

    # Pembayaran (Kredit)
    for p in payments_qs:
        writer.writerow([
            'Pembayaran',
            p.payment_date.strftime('%Y-%m-%d'),
            getattr(p.rental, 'invoice_number', ''),
            p.method,
            p.amount,
            '',
        ])

    # Biaya Lain (Debit)
    for o in other_qs:
        writer.writerow([
            'Biaya Lain',
            o.expense_date.strftime('%Y-%m-%d'),
            o.reference_number,
            o.description,
            '',
            o.total_cost,
        ])

    # Maintenance (Debit)
    for m in maintenance_qs:
        writer.writerow([
            'Maintenance',
            m.maintenance_date.strftime('%Y-%m-%d'),
            m.vendor.name if m.vendor else '',
            m.issue_description,
            '',
            m.total_cost,
        ])

    # Order Rental (Informasi saja)
    for r in rentals_qs:
        writer.writerow([
            'Order Rental',
            r.start_at.strftime('%Y-%m-%d'),
            r.invoice_number,
            r.customer.full_name if r.customer else '',
            '',
            '',
        ])

    return response


from django.urls import path


@require_POST
def vehicle_photo_upload(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    count = VehiclePhoto.objects.filter(vehicle=vehicle).count()
    if count >= 5:
        return JsonResponse({"ok": False, "error": "Maksimal 5 foto per kendaraan."}, status=400)

    image = request.FILES.get("image")
    if not image:
        return JsonResponse({"ok": False, "error": "Pilih gambar untuk diupload."}, status=400)

    if image.size > MAX_FILE_SIZE:
        return JsonResponse({"ok": False, "error": "Ukuran gambar maksimal 1 MB."}, status=400)

    try:
        url = upload_to_supabase(image, vehicle.id)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"Gagal upload: {e}"}, status=500)

    last_order = VehiclePhoto.objects.filter(vehicle=vehicle).count()
    photo = VehiclePhoto(vehicle=vehicle, url=url, order=last_order + 1)
    photo.save()

    return JsonResponse({
        "ok": True,
        "photo": {
            "id": photo.id,
            "url": photo.url,
            "order": photo.order,
        }
    })


@require_POST
def vehicle_photo_delete(request, vehicle_id, photo_id):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    photo = get_object_or_404(VehiclePhoto, pk=photo_id, vehicle=vehicle)
    photo.delete()
    return JsonResponse({"ok": True})


@require_POST
def vehicle_photo_update_order(request, vehicle_id, photo_id):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    photo = get_object_or_404(VehiclePhoto, pk=photo_id, vehicle=vehicle)
    new_order = request.POST.get("order")
    if new_order is not None:
        photo.order = int(new_order)
        photo.save(update_fields=["order"])
    return JsonResponse({"ok": True})


def _get_urls():
    urls = admin.AdminSite.get_urls(admin.site)
    my_urls = [
        path('rentals/booking-calendar/', admin.site.admin_view(booking_calendar), name='rental_booking_calendar'),
        path('rentals/booking-calendar/events/', admin.site.admin_view(booking_calendar_events), name='rental_booking_calendar_events'),
        path('rentals/booking-calendar/reschedule/', admin.site.admin_view(booking_calendar_reschedule), name='rental_booking_calendar_reschedule'),
        path('rentals/financial-report/', admin.site.admin_view(financial_report), name='rental_financial_report'),
        path('rentals/financial-report/export/', admin.site.admin_view(financial_report_csv), name='rental_financial_report_export'),
        path('rentals/vehicle/<int:vehicle_id>/photos/upload/', admin.site.admin_view(vehicle_photo_upload), name='vehicle_photo_upload'),
        path('rentals/vehicle/<int:vehicle_id>/photos/<int:photo_id>/delete/', admin.site.admin_view(vehicle_photo_delete), name='vehicle_photo_delete'),
        path('rentals/vehicle/<int:vehicle_id>/photos/<int:photo_id>/order/', admin.site.admin_view(vehicle_photo_update_order), name='vehicle_photo_update_order'),
    ]
    return my_urls + urls

admin.site.get_urls = _get_urls
