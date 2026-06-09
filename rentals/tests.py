from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone

from .admin import RentalAdmin, rental_admin_app_index
from .dashboard import apply_rental_menu_groups, get_dashboard_context, group_rental_menu
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
        self.create_rental(invoice_number='Order rental-2026-001')

        rental = self.create_rental(start_at=timezone.datetime(2026, 5, 26, 7, 13, tzinfo=timezone.get_current_timezone()))

        self.assertEqual(rental.invoice_number, 'Order rental-2026-002')

    def test_auto_invoice_number_can_exceed_three_digits(self):
        self.create_rental(invoice_number='Order rental-2026-999')

        rental = self.create_rental(start_at=timezone.datetime(2026, 5, 26, 7, 13, tzinfo=timezone.get_current_timezone()))

        self.assertEqual(rental.invoice_number, 'Order rental-2026-1000')

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
        self.assertEqual(len(app_list[1]['menu_groups']), 2)
        self.assertEqual(app_list[1]['menu_groups'][0]['title'], 'Master Data')
        self.assertEqual(app_list[1]['menu_groups'][1]['title'], 'Keuangan')

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


class DashboardContextTests(TestCase):
    def setUp(self):
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
        self.assertEqual(context['monthly_income'], 'Rp300.000,00')
        self.assertEqual(context['monthly_expenses'], 'Rp450.000,00')

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

        self.assertEqual(context['monthly_expenses'], 'Rp700.000,00')

    def test_rentals_app_index_redirects_to_admin_home(self):
        request = RequestFactory().get('/admin/rentals/', {'period': '2026-05'})
        response = rental_admin_app_index(request, 'rentals')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin/?period=2026-05')
