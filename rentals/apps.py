from django.apps import AppConfig


class RentalsConfig(AppConfig):
    name = 'rentals'
    verbose_name = 'POS Rental'

    def ready(self):
        import rentals.signals  # noqa
