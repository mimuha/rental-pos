import json
from datetime import datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .admin import RentalAdmin, rental_admin_app_index
from .dashboard import apply_rental_menu_groups, get_dashboard_context, group_rental_menu
from .forms import RupiahField, RupiahWidget
from .middleware import LoginRateLimitMiddleware
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
    UserThemePreference,
)


class RentalInvoiceNumberTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            full_name='Atep Tatang',
            identity_number='ID-001',
            phone_number='08123456789',
            address='Bandung',
        )
        category = VehicleCategory.objects.create(name='MPV')
        self.vehicle = Vehicle.objects.create(
            category=category,
            plate_number='B2702SED',
            brand='Toyota',
            model='Avanza',
            year=2024,
            transmission=Vehicle.Transmission.MANUAL,
            fuel_type=Vehicle.FuelType.GASOLINE,
            daily_rate=Decimal('150000.00'),
            odometer=1000,
        )
        self.user = get_user_model().objects.create_superuser(
            username='testadmin',
            email='test@example.com',
            password='password123',
        )

    def create_rental(self, invoice_number='', start_at=None):
        if start_at is None:
            start_at = timezone.datetime(2026, 5, 24, 7, 13, tzinfo=timezone.get_current_timezone())
        return Rental.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            invoice_number=invoice_number,
            start_at=start_at,
            expected_return_at=start_at + timedelta(days=1),
            start_odometer=1000,
            daily_rate=Decimal('150000.00'),
        )

    def test_auto_invoice_number_continues_existing_sequence(self):
        self.create_rental(invoice_number='order-rental-2026-001')

        rental = self.create_rental(start_at=timezone.datetime(2026, 5, 26, 7, 13, tzinfo=timezone.get_current_timezone()))

        self.assertEqual(rental.invoice_number, 'order-rental-2026-002')

    def test_auto_invoice_number_can_exceed_three_digits(self):
        self.create_rental(invoice_number='order-rental-2026-999')

        rental = self.create_rental(start_at=timezone.datetime(2026, 5, 26, 7, 13, tzinfo=timezone.get_current_timezone()))

        self.assertEqual(rental.invoice_number, 'order-rental-2026-1000')

    def test_rental_status_defaults_to_draft(self):
        rental = self.create_rental()

        self.assertEqual(rental.status, Rental.Status.DRAFT)

    def test_admin_activate_button_changes_draft_to_active(self):
        rental = self.create_rental()
        request = self.build_admin_post_request({'_activate_rental': '1'})

        RentalAdmin(Rental, AdminSite()).response_change(request, rental)
        rental.refresh_from_db()

        self.assertEqual(rental.status, Rental.Status.ACTIVE)

    def test_admin_complete_button_changes_active_to_completed(self):
        rental = self.create_rental()
        rental.status = Rental.Status.ACTIVE
        rental.save(update_fields=['status', 'updated_at'])
        request = self.build_admin_post_request({'_complete_rental': '1'})

        RentalAdmin(Rental, AdminSite()).response_change(request, rental)
        rental.refresh_from_db()

        self.assertEqual(rental.status, Rental.Status.COMPLETED)

    def build_admin_post_request(self, data):
        request = RequestFactory().post('/admin/rentals/rental/1/change/', data)
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request


class VehicleMaintenanceTests(TestCase):
    def setUp(self):
        category = VehicleCategory.objects.create(name='MPV')
        self.vehicle = Vehicle.objects.create(
            category=category,
            plate_number='D1234ABC',
            brand='Toyota',
            model='Avanza',
            year=2024,
            transmission=Vehicle.Transmission.MANUAL,
            fuel_type=Vehicle.FuelType.GASOLINE,
            daily_rate=Decimal('150000.00'),
            odometer=25000,
        )
        self.maintenance_category = MaintenanceCategory.objects.get(name='Penggantian oli')
        self.vendor = MaintenanceVendor.objects.create(
            name='Bengkel Maju Jaya',
            phone_number='022123456',
        )

    def test_create_vehicle_maintenance_with_cost_and_vendor(self):
        maintenance = VehicleMaintenance.objects.create(
            vehicle=self.vehicle,
            category=self.maintenance_category,
            vendor=self.vendor,
            odometer=25200,
            issue_description='Ganti oli mesin rutin.',
            parts_replaced='Oli mesin 4 liter, filter oli',
            total_cost=Decimal('450000.00'),
        )

        self.assertEqual(maintenance.status, VehicleMaintenance.Status.COMPLETED)
        self.assertEqual(maintenance.total_cost, Decimal('450000.00'))
        self.assertEqual(maintenance.vendor.name, 'Bengkel Maju Jaya')


class OtherExpenseTests(TestCase):
    def test_create_other_expense_with_type_and_cost(self):
        expense_type = ExpenseType.objects.get(name='Alat kerja kantor')
        expense = OtherExpense.objects.create(
            expense_type=expense_type,
            payee='Toko ATK Bandung',
            description='Pembelian printer dan kertas A4.',
            total_cost=Decimal('750000.00'),
        )

        self.assertEqual(expense.status, OtherExpense.Status.COMPLETED)
        self.assertEqual(expense.total_cost, Decimal('750000.00'))
        self.assertEqual(expense.expense_type.name, 'Alat kerja kantor')


class RentalMenuGroupTests(TestCase):
    def test_group_rental_menu_orders_models_by_section(self):
        models = [
            {'object_name': 'Payment', 'name': 'Order payment'},
            {'object_name': 'MaintenanceVendor', 'name': 'Daftar bengkel'},
            {'object_name': 'OtherExpense', 'name': 'Kas kecil'},
            {'object_name': 'Rental', 'name': 'Order rental'},
        ]
        groups = group_rental_menu(models)

        self.assertEqual([group['title'] for group in groups], ['Master Data', 'Transaksi', 'Keuangan'])
        self.assertEqual(groups[0]['models'][0]['name'], 'Daftar bengkel')
        self.assertEqual(groups[1]['models'][0]['name'], 'Order rental')
        self.assertEqual(groups[1]['models'][1]['name'], 'Order payment')
        self.assertEqual(groups[2]['models'][0]['name'], 'Kas kecil')

    def test_apply_rental_menu_groups_updates_rentals_app(self):
        app_list = [
            {
                'app_label': 'auth',
                'models': [{'object_name': 'User', 'name': 'Pengguna'}],
            },
            {
                'app_label': 'rentals',
                'models': [
                    {'object_name': 'Vehicle', 'name': 'Daftar kendaraan'},
                    {'object_name': 'OtherExpense', 'name': 'Kas kecil'},
                ],
            },
        ]
        apply_rental_menu_groups(app_list)

        self.assertNotIn('menu_groups', app_list[0])
        self.assertEqual(len(app_list[1]['menu_groups']), 3)
        self.assertEqual(app_list[1]['menu_groups'][0]['title'], 'Master Data')
        self.assertEqual(app_list[1]['menu_groups'][1]['title'], 'Transaksi')
        self.assertEqual(app_list[1]['menu_groups'][2]['title'], 'Keuangan')
        self.assertEqual(
            app_list[1]['menu_groups'][1]['models'][0]['object_name'],
            'bookingcalendar',
        )
        self.assertEqual(
            app_list[1]['menu_groups'][2]['models'][-1]['object_name'],
            'financialreport',
        )

    def test_rental_admin_each_context_applies_menu_groups_to_available_apps(self):
        User = get_user_model()
        request = RequestFactory().get('/admin/')
        request.user = User.objects.create_superuser(
            username='admin_user',
            email='admin@example.com',
            password='password123',
        )
        context = admin.site.each_context(request)
        rentals_app = next((app for app in context['available_apps'] if app['app_label'] == 'rentals'), None)

        self.assertIsNotNone(rentals_app)
        self.assertIn('menu_groups', rentals_app)
        self.assertEqual(rentals_app['menu_groups'][0]['title'], 'Master Data')


@override_settings(DASHBOARD_CACHE_SECONDS=0)
class DashboardContextTests(TestCase):
    def setUp(self):
        cache.clear()
        category = VehicleCategory.objects.create(name='MPV')
        self.vehicle = Vehicle.objects.create(
            category=category,
            plate_number='B2702SED',
            brand='Toyota',
            model='Avanza',
            year=2024,
            transmission=Vehicle.Transmission.MANUAL,
            fuel_type=Vehicle.FuelType.GASOLINE,
            daily_rate=Decimal('150000.00'),
            odometer=1000,
        )
        self.maintenance_category = MaintenanceCategory.objects.get(name='Penggantian oli')
        self.vendor = MaintenanceVendor.objects.create(name='Bengkel Maju Jaya')

    def test_dashboard_sums_income_and_expenses_for_selected_month(self):
        customer = Customer.objects.create(
            full_name='Atep Tatang',
            identity_number='ID-002',
            phone_number='08123456789',
            address='Bandung',
        )
        start_at = timezone.datetime(2026, 4, 10, 8, 0, tzinfo=timezone.get_current_timezone())
        rental = Rental.objects.create(
            customer=customer,
            vehicle=self.vehicle,
            start_at=start_at,
            expected_return_at=start_at + timedelta(days=1),
            start_odometer=1000,
            daily_rate=Decimal('150000.00'),
        )
        Payment.objects.create(
            rental=rental,
            payment_date=timezone.datetime(2026, 4, 15, 10, 0, tzinfo=timezone.get_current_timezone()),
            method=Payment.Method.CASH,
            amount=Decimal('300000.00'),
        )
        VehicleMaintenance.objects.create(
            vehicle=self.vehicle,
            category=self.maintenance_category,
            vendor=self.vendor,
            maintenance_date=timezone.datetime(2026, 4, 20, 9, 0, tzinfo=timezone.get_current_timezone()),
            issue_description='Service rutin',
            total_cost=Decimal('450000.00'),
        )

        request = RequestFactory().get('/admin/', {'period': '2026-04'})
        context = get_dashboard_context(request)

        self.assertEqual(context['selected_period'], '2026-04')
        self.assertEqual(context['selected_period_label'], 'April 2026')
        self.assertEqual(context['monthly_income'], 'Rp 300rb')
        self.assertEqual(context['monthly_expenses'], 'Rp 450rb')

    def test_dashboard_includes_other_expenses_in_monthly_total(self):
        VehicleMaintenance.objects.create(
            vehicle=self.vehicle,
            category=self.maintenance_category,
            vendor=self.vendor,
            maintenance_date=timezone.datetime(2026, 4, 20, 9, 0, tzinfo=timezone.get_current_timezone()),
            issue_description='Service rutin',
            total_cost=Decimal('450000.00'),
        )
        expense_type = ExpenseType.objects.get(name='Pajak kendaraan')
        OtherExpense.objects.create(
            expense_type=expense_type,
            expense_date=timezone.datetime(2026, 4, 5, 9, 0, tzinfo=timezone.get_current_timezone()),
            description='Pajak tahunan mobil rental.',
            total_cost=Decimal('250000.00'),
        )

        request = RequestFactory().get('/admin/', {'period': '2026-04'})
        context = get_dashboard_context(request)

        self.assertEqual(context['monthly_expenses'], 'Rp 700rb')

    def test_rentals_app_index_redirects_to_admin_home(self):
        request = RequestFactory().get('/admin/rentals/', {'period': '2026-05'})
        response = rental_admin_app_index(request, 'rentals')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin/?period=2026-05')


class RentalSignalConsistencyTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            full_name='Atep Tatang',
            identity_number='ID-SIGNAL',
            phone_number='08123456789',
            address='Bandung',
        )
        self.category = VehicleCategory.objects.create(name='MPV Signal')
        self.vehicle = Vehicle.objects.create(
            category=self.category,
            plate_number='B9001SIG',
            brand='Toyota',
            model='Avanza',
            year=2024,
            transmission=Vehicle.Transmission.MANUAL,
            fuel_type=Vehicle.FuelType.GASOLINE,
            daily_rate=Decimal('150000.00'),
            odometer=1000,
        )
        self.start_at = timezone.make_aware(datetime(2026, 5, 24, 7, 0))

    def create_rental(self, **kwargs):
        defaults = {
            'customer': self.customer,
            'vehicle': self.vehicle,
            'start_at': self.start_at,
            'expected_return_at': self.start_at + timedelta(days=1),
            'start_odometer': 1000,
            'daily_rate': Decimal('150000.00'),
        }
        defaults.update(kwargs)
        return Rental.objects.create(**defaults)

    def linked_expense(self, rental):
        return OtherExpense.objects.filter(
            rental=rental,
            expense_type__name='Biaya Operasional Perjalanan',
        ).first()

    def test_update_fields_excluding_fee_does_not_create_expense(self):
        rental = self.create_rental()
        rental.additional_fee = Decimal('75000.00')

        rental.save(update_fields=['status', 'updated_at'])
        rental.refresh_from_db()

        self.assertEqual(rental.additional_fee, Decimal('0.00'))
        self.assertIsNone(self.linked_expense(rental))

    def test_update_fields_including_fee_keeps_expense_in_sync(self):
        rental = self.create_rental()
        rental.additional_fee = Decimal('75000.00')
        rental.save(update_fields=['additional_fee', 'updated_at'])

        expense = self.linked_expense(rental)
        self.assertIsNotNone(expense)
        self.assertEqual(expense.total_cost, Decimal('75000.00'))

        rental.additional_fee = Decimal('125000.00')
        rental.save(update_fields=['additional_fee', 'updated_at'])
        expense.refresh_from_db()
        self.assertEqual(expense.total_cost, Decimal('125000.00'))

        rental.additional_fee = Decimal('0.00')
        rental.save(update_fields=['additional_fee', 'updated_at'])
        self.assertIsNone(self.linked_expense(rental))

    def test_created_active_rental_syncs_vehicle_and_expense(self):
        rental = self.create_rental(
            status=Rental.Status.ACTIVE,
            additional_fee=Decimal('50000.00'),
        )

        self.vehicle.refresh_from_db()
        expense = self.linked_expense(rental)
        self.assertEqual(self.vehicle.status, Vehicle.Status.RENTED)
        self.assertIsNotNone(expense)
        self.assertEqual(expense.status, OtherExpense.Status.IN_PROGRESS)


class VehiclePhotoModelTests(TestCase):
    def test_vehicle_photo_table_is_available(self):
        category = VehicleCategory.objects.create(name='MPV Photo')
        vehicle = Vehicle.objects.create(
            category=category,
            plate_number='B9002PHT',
            brand='Toyota',
            model='Avanza',
            year=2024,
            transmission=Vehicle.Transmission.MANUAL,
            fuel_type=Vehicle.FuelType.GASOLINE,
            daily_rate=Decimal('150000.00'),
            odometer=1000,
        )

        photo = VehiclePhoto.objects.create(
            vehicle=vehicle,
            url='https://example.com/photo.jpg',
            order=1,
        )

        self.assertEqual(VehiclePhoto.objects.filter(vehicle=vehicle).count(), 1)
        self.assertEqual(photo.order, 1)


@override_settings(SECURE_SSL_REDIRECT=False)
class BookingCalendarRescheduleTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username='reschedule_admin',
            email='reschedule@example.com',
            password='password123',
        )
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(
            full_name='Atep Tatang',
            identity_number='ID-RESCHEDULE',
            phone_number='08123456789',
            address='Bandung',
        )
        self.category = VehicleCategory.objects.create(name='MPV Reschedule')
        self.vehicle = Vehicle.objects.create(
            category=self.category,
            plate_number='B9003RSC',
            brand='Toyota',
            model='Avanza',
            year=2024,
            transmission=Vehicle.Transmission.MANUAL,
            fuel_type=Vehicle.FuelType.GASOLINE,
            daily_rate=Decimal('150000.00'),
            odometer=1000,
        )
        self.url = reverse('admin:rental_booking_calendar_reschedule')

    def create_rental(self, start_at):
        return Rental.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            start_at=start_at,
            expected_return_at=start_at + timedelta(days=1),
            start_odometer=1000,
            daily_rate=Decimal('150000.00'),
        )

    def reschedule(self, rental, new_date):
        return self.client.post(
            self.url,
            data=json.dumps({
                'event_id': f'rental-{rental.pk}',
                'start': new_date,
            }),
            content_type='application/json',
        )

    def test_reschedule_preserves_midnight_start_time(self):
        rental = self.create_rental(timezone.make_aware(datetime(2026, 5, 24, 0, 0)))

        response = self.reschedule(rental, '2026-06-01')
        rental.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(timezone.localtime(rental.start_at).time(), time(0, 0))
        self.assertEqual(
            rental.expected_return_at - rental.start_at,
            timedelta(days=1),
        )

    def test_reschedule_handles_nonexistent_dst_time(self):
        tz = ZoneInfo('America/New_York')
        with timezone.override(tz):
            rental = self.create_rental(datetime(2026, 3, 1, 2, 30, tzinfo=tz))

            response = self.reschedule(rental, '2026-03-08')
            rental.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        local_start = rental.start_at.astimezone(tz)
        self.assertEqual((local_start.hour, local_start.minute), (3, 0))

    def test_reschedule_handles_ambiguous_dst_time(self):
        tz = ZoneInfo('America/New_York')
        with timezone.override(tz):
            rental = self.create_rental(datetime(2026, 10, 1, 1, 30, tzinfo=tz))

            response = self.reschedule(rental, '2026-11-01')
            rental.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        local_start = rental.start_at.astimezone(tz)
        self.assertEqual((local_start.hour, local_start.minute), (1, 30))
        self.assertEqual(local_start.fold, 0)


    def test_reschedule_rejects_non_numeric_event_id(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                'event_id': 'rental-abc',
                'start': '2026-06-01',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])

    def test_reschedule_rejects_cancelled_rental(self):
        rental = self.create_rental(timezone.make_aware(datetime(2026, 5, 24, 7, 0)))
        rental.status = Rental.Status.CANCELLED
        rental.save(update_fields=['status', 'updated_at'])

        response = self.reschedule(rental, '2026-06-01')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])


class RentalCancellationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username='cancel_admin',
            email='cancel@example.com',
            password='password123',
        )
        self.customer = Customer.objects.create(
            full_name='Atep Tatang',
            identity_number='ID-CANCEL',
            phone_number='08123456789',
            address='Bandung',
        )
        self.category = VehicleCategory.objects.create(name='MPV Cancel')
        self.vehicle = Vehicle.objects.create(
            category=self.category,
            plate_number='B9004CNL',
            brand='Toyota',
            model='Avanza',
            year=2024,
            transmission=Vehicle.Transmission.MANUAL,
            fuel_type=Vehicle.FuelType.GASOLINE,
            daily_rate=Decimal('150000.00'),
            odometer=1000,
        )
        self.start_at = timezone.make_aware(datetime(2026, 7, 1, 9, 0))

    def create_rental(self, start_at=None, **kwargs):
        if start_at is None:
            start_at = self.start_at
        defaults = {
            'customer': self.customer,
            'vehicle': self.vehicle,
            'start_at': start_at,
            'expected_return_at': start_at + timedelta(days=1),
            'start_odometer': 1000,
            'daily_rate': Decimal('150000.00'),
        }
        defaults.update(kwargs)
        return Rental.objects.create(**defaults)

    def linked_expense(self, rental):
        return OtherExpense.objects.filter(
            rental=rental,
            expense_type__name='Biaya Operasional Perjalanan',
        ).first()

    def build_admin_post_request(self, data):
        request = RequestFactory().post('/admin/rentals/rental/1/change/', data)
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_cancelled_rental_releases_vehicle_and_expenses(self):
        rental = self.create_rental(
            status=Rental.Status.ACTIVE,
            additional_fee=Decimal('50000.00'),
        )
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.RENTED)

        rental.status = Rental.Status.CANCELLED
        rental.save(update_fields=['status', 'updated_at'])

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.AVAILABLE)
        self.assertEqual(self.linked_expense(rental).status, OtherExpense.Status.CANCELLED)

    def test_admin_cancel_button_cancels_active_rental(self):
        rental = self.create_rental(status=Rental.Status.ACTIVE)
        request = self.build_admin_post_request({'_cancel_rental': '1'})

        RentalAdmin(Rental, AdminSite()).response_change(request, rental)
        rental.refresh_from_db()

        self.assertEqual(rental.status, Rental.Status.CANCELLED)

    def test_delete_allowed_only_for_draft_rentals(self):
        model_admin = RentalAdmin(Rental, AdminSite())
        request = RequestFactory().get('/admin/')
        request.user = self.user
        draft = self.create_rental(
            start_at=self.start_at,
            status=Rental.Status.DRAFT,
        )
        active = self.create_rental(
            start_at=self.start_at + timedelta(days=5),
            status=Rental.Status.ACTIVE,
        )

        self.assertTrue(model_admin.has_delete_permission(request, draft))
        self.assertFalse(model_admin.has_delete_permission(request, active))


@override_settings(SECURE_SSL_REDIRECT=False)
class RentalDraftOverlapTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username='draft_admin',
            email='draft@example.com',
            password='password123',
        )
        self.customer = Customer.objects.create(
            full_name='Atep Tatang',
            identity_number='ID-DRAFT',
            phone_number='08123456789',
            address='Bandung',
        )
        self.category = VehicleCategory.objects.create(name='MPV Draft')
        self.vehicle = Vehicle.objects.create(
            category=self.category,
            plate_number='B9005DRF',
            brand='Toyota',
            model='Avanza',
            year=2024,
            transmission=Vehicle.Transmission.MANUAL,
            fuel_type=Vehicle.FuelType.GASOLINE,
            daily_rate=Decimal('150000.00'),
            odometer=1000,
        )
        self.start_at = timezone.make_aware(datetime(2026, 8, 1, 9, 0))

    def create_rental(self, start_at=None, **kwargs):
        if start_at is None:
            start_at = self.start_at
        defaults = {
            'customer': self.customer,
            'vehicle': self.vehicle,
            'start_at': start_at,
            'expected_return_at': start_at + timedelta(days=2),
            'start_odometer': 1000,
            'daily_rate': Decimal('150000.00'),
        }
        defaults.update(kwargs)
        return Rental.objects.create(**defaults)

    def test_active_rental_can_be_created_over_a_draft(self):
        self.create_rental(status=Rental.Status.DRAFT)

        rental = self.create_rental(status=Rental.Status.ACTIVE)

        self.assertEqual(rental.status, Rental.Status.ACTIVE)

    def test_drafts_do_not_block_each_other(self):
        self.create_rental(status=Rental.Status.DRAFT)
        second = self.create_rental(status=Rental.Status.DRAFT)

        self.assertEqual(second.status, Rental.Status.DRAFT)

    def test_draft_cannot_overlap_a_confirmed_rental(self):
        self.create_rental(status=Rental.Status.ACTIVE)

        with self.assertRaises(ValidationError):
            self.create_rental(status=Rental.Status.DRAFT)

    def test_draft_calendar_is_not_marked_busy(self):
        draft = self.create_rental(status=Rental.Status.DRAFT)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('admin:rental_booking_calendar_events'),
            {'start': '2026-08-01', 'end': '2026-08-05'},
        )
        events = response.json()

        self.assertTrue(any(event['id'] == f'rental-{draft.pk}' for event in events))
        self.assertTrue(any(
            event['id'].startswith(f'available-{self.vehicle.pk}-')
            for event in events
        ))

    def test_activating_conflicting_draft_keeps_it_as_draft(self):
        draft = self.create_rental(status=Rental.Status.DRAFT)
        self.create_rental(status=Rental.Status.ACTIVE)

        request = RequestFactory().post('/admin/rentals/rental/1/change/', {'_activate_rental': '1'})
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)

        RentalAdmin(Rental, AdminSite()).response_change(request, draft)
        draft.refresh_from_db()

        self.assertEqual(draft.status, Rental.Status.DRAFT)


class RupiahFieldTests(TestCase):
    def test_clean_accepts_indonesian_format(self):
        field = RupiahField(max_digits=12, decimal_places=2)

        self.assertEqual(field.clean('1.500.000'), Decimal('1500000'))
        self.assertEqual(field.clean('1.500.000,50'), Decimal('1500000.50'))
        self.assertEqual(field.clean('Rp 2.000.000'), Decimal('2000000'))

    def test_clean_accepts_legacy_decimal_format(self):
        field = RupiahField(max_digits=12, decimal_places=2)

        self.assertEqual(field.clean('1500.50'), Decimal('1500.50'))

    def test_clean_rejects_invalid_value(self):
        field = RupiahField(max_digits=12, decimal_places=2)

        with self.assertRaises(ValidationError):
            field.clean('abc')

    def test_widget_formats_currency_without_trailing_zeroes(self):
        widget = RupiahWidget()

        self.assertEqual(widget.format_value(Decimal('1500000')), '1.500.000')
        self.assertEqual(widget.format_value(Decimal('1500000.50')), '1.500.000,50')

    def test_rental_money_field_uses_rupiah_field(self):
        request = RequestFactory().get('/admin/')
        form_field = RentalAdmin(Rental, AdminSite()).formfield_for_dbfield(
            Rental._meta.get_field('daily_rate'),
            request,
        )

        self.assertIsInstance(form_field, RupiahField)


class LoginRateLimitMiddlewareTests(TestCase):
    def setUp(self):
        cache.clear()

    def build_request(self, remote_addr, forwarded_for=None):
        meta = {'REMOTE_ADDR': remote_addr}
        if forwarded_for is not None:
            meta['HTTP_X_FORWARDED_FOR'] = forwarded_for
        return RequestFactory().post('/admin/login/', **meta)

    def call_middleware(self, request):
        middleware = LoginRateLimitMiddleware(lambda req: HttpResponse(status=200))
        return middleware(request)

    @override_settings(TRUSTED_PROXY_COUNT=0)
    def test_x_forwarded_for_spoofing_does_not_bypass_limit(self):
        for index in range(5):
            self.call_middleware(
                self.build_request('10.0.0.5', f'198.51.100.{index}')
            )

        response = self.call_middleware(
            self.build_request('10.0.0.5', '203.0.113.99')
        )

        self.assertEqual(response.status_code, 429)

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_trusted_proxy_uses_client_ip_from_forwarded_header(self):
        for _ in range(5):
            self.call_middleware(
                self.build_request('10.0.0.6', '203.0.113.10')
            )

        response = self.call_middleware(
            self.build_request('10.0.0.6', '203.0.113.11')
        )

        self.assertEqual(response.status_code, 200)


@override_settings(SECURE_SSL_REDIRECT=False)
class ThemePreferenceTests(TestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username='theme_admin',
            email='theme@example.com',
            password='password123',
        )

    def test_default_preference(self):
        preference = UserThemePreference.objects.create(user=self.user)

        self.assertEqual(preference.mode, UserThemePreference.Mode.AUTO)
        self.assertEqual(preference.accent, UserThemePreference.Accent.PURPLE)

    def test_endpoint_saves_preference(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('admin:rental_theme_preference'),
            data=json.dumps({'mode': 'dark', 'accent': 'orange'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        preference = UserThemePreference.objects.get(user=self.user)
        self.assertEqual(preference.mode, UserThemePreference.Mode.DARK)
        self.assertEqual(preference.accent, UserThemePreference.Accent.ORANGE)

    def test_endpoint_rejects_invalid_choice(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('admin:rental_theme_preference'),
            data=json.dumps({'mode': 'neon', 'accent': 'orange'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(UserThemePreference.objects.filter(user=self.user).exists())

    def test_context_processor_returns_saved_preference(self):
        from .context_processors import theme_preference

        request = RequestFactory().get('/admin/')
        request.user = self.user

        self.assertEqual(theme_preference(request)['theme_mode'], 'auto')

        UserThemePreference.objects.create(
            user=self.user,
            mode=UserThemePreference.Mode.DARK,
            accent=UserThemePreference.Accent.ORANGE,
        )
        context = theme_preference(request)

        self.assertEqual(context['theme_mode'], 'dark')
        self.assertEqual(context['theme_accent'], 'orange')

    def test_admin_page_renders_saved_theme(self):
        UserThemePreference.objects.create(
            user=self.user,
            mode=UserThemePreference.Mode.DARK,
            accent=UserThemePreference.Accent.ORANGE,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-theme="dark"')
        self.assertContains(response, 'data-accent="orange"')
        self.assertContains(response, 'rental-theme-settings')
        self.assertContains(response, 'gitlab_theme.css')


@override_settings(SECURE_SSL_REDIRECT=False, DASHBOARD_CACHE_SECONDS=0)
class AdminQueryBudgetTests(TestCase):
    """Menjaga optimasi N+1 dan round trip admin agar tidak regresi."""

    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_superuser(
            username='budget_admin',
            email='budget@example.com',
            password='password123',
        )
        self.customer = Customer.objects.create(
            full_name='Budi Budget',
            identity_number='ID-BUDGET',
            phone_number='08120000000',
            address='Jakarta',
        )
        category = VehicleCategory.objects.create(name='SUV')
        start = timezone.now().replace(microsecond=0) + timedelta(days=10)
        self.rentals = []
        for index in range(5):
            vehicle = Vehicle.objects.create(
                category=category,
                plate_number=f'B100{index}BD',
                brand='Toyota',
                model='Rush',
                year=2024,
                transmission=Vehicle.Transmission.AUTOMATIC,
                fuel_type=Vehicle.FuelType.GASOLINE,
                daily_rate=Decimal('200000.00'),
                odometer=1000,
            )
            rental = Rental.objects.create(
                customer=self.customer,
                vehicle=vehicle,
                start_at=start + timedelta(days=index * 3),
                expected_return_at=start + timedelta(days=index * 3 + 2),
                start_odometer=1000,
                daily_rate=Decimal('200000.00'),
                status=Rental.Status.COMPLETED,
            )
            for _ in range(2):
                Payment.objects.create(
                    rental=rental,
                    method=Payment.Method.CASH,
                    amount=Decimal('100000.00'),
                )
            self.rentals.append(rental)

    def _captured_sql(self, url):
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return [query['sql'].lower() for query in captured.captured_queries]

    def test_rental_changelist_prefetches_payments(self):
        self.client.force_login(self.user)

        sql = self._captured_sql(reverse('admin:rentals_rental_changelist'))

        payment_queries = [query for query in sql if 'from "rentals_payment"' in query]
        self.assertLessEqual(
            len(payment_queries),
            1,
            f'Changelist Rental melakukan {len(payment_queries)} query pembayaran (N+1).',
        )

    def test_payment_changelist_avoids_customer_n_plus_one(self):
        self.client.force_login(self.user)

        sql = self._captured_sql(reverse('admin:rentals_payment_changelist'))

        customer_queries = [query for query in sql if 'from "rentals_customer"' in query]
        self.assertLessEqual(
            len(customer_queries),
            1,
            f'Changelist Payment melakukan {len(customer_queries)} query pelanggan (N+1).',
        )

    def test_dashboard_counts_vehicles_in_single_query(self):
        self.client.force_login(self.user)

        sql = self._captured_sql(reverse('admin:index'))

        count_queries = [
            query for query in sql
            if 'count(' in query and 'rentals_vehicle' in query
        ]
        self.assertLessEqual(
            len(count_queries),
            1,
            f'Dashboard menghitung kendaraan lewat {len(count_queries)} query.',
        )

    def test_status_only_save_does_not_lock_vehicle(self):
        rental = self.rentals[0]
        rental.status = Rental.Status.CANCELLED

        with CaptureQueriesContext(connection) as captured:
            rental.save(update_fields=['status', 'updated_at'])

        rental.refresh_from_db()
        self.assertEqual(rental.status, Rental.Status.CANCELLED)

        sql = ' '.join(query['sql'].lower() for query in captured.captured_queries)
        self.assertNotIn('for update', sql)

    def test_rental_add_form_uses_autocomplete(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('admin:rentals_rental_add'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin-autocomplete')

    def test_payment_add_form_uses_autocomplete(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('admin:rentals_payment_add'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin-autocomplete')
