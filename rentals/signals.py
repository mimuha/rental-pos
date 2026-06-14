from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Rental, OtherExpense, ExpenseType, Vehicle

EXPENSE_TYPE_NAME = 'Biaya Operasional Perjalanan'


def _get_expense_type():
    expense_type, _ = ExpenseType.objects.get_or_create(
        name=EXPENSE_TYPE_NAME,
        defaults={'description': 'Biaya operasional terkait perjalanan rental'},
    )
    return expense_type


def _get_linked_expense(instance, expense_type):
    return instance.other_expenses.filter(expense_type=expense_type).first()


def _build_description(instance):
    return instance.additional_fee_description or f'Biaya tambahan order {instance.invoice_number}'


@receiver(post_save, sender=Rental)
def handle_rental_other_expenses(sender, instance, created, **kwargs):
    expense_type = _get_expense_type()
    previous_status = getattr(instance, '_previous_status', None)
    status_changed = previous_status is not None and previous_status != instance.status
    previous_fee = getattr(instance, '_previous_additional_fee', None)
    fee_changed = previous_fee is not None and previous_fee != instance.additional_fee
    previous_desc = getattr(instance, '_previous_additional_fee_description', None)
    desc_changed = previous_desc is not None and previous_desc != instance.additional_fee_description
    linked_expense = _get_linked_expense(instance, expense_type)
    description = _build_description(instance)

    if created:
        if instance.additional_fee > 0:
            OtherExpense.objects.create(
                rental=instance,
                expense_type=expense_type,
                expense_date=instance.start_at or timezone.now(),
                description=description,
                total_cost=instance.additional_fee,
                status=OtherExpense.Status.PLANNED,
                reference_number=f'dari {instance.invoice_number}',
            )
    else:
        if fee_changed or desc_changed:
            if instance.additional_fee > 0:
                update_fields = []
                if linked_expense:
                    if fee_changed:
                        linked_expense.total_cost = instance.additional_fee
                        update_fields.append('total_cost')
                    if desc_changed:
                        linked_expense.description = description
                        update_fields.append('description')
                    if update_fields:
                        update_fields.append('updated_at')
                        linked_expense.save(update_fields=update_fields)
                else:
                    OtherExpense.objects.create(
                        rental=instance,
                        expense_type=expense_type,
                        expense_date=instance.start_at or timezone.now(),
                        description=description,
                        total_cost=instance.additional_fee,
                        status=OtherExpense.Status.PLANNED,
                        reference_number=f'dari {instance.invoice_number}',
                    )
            elif linked_expense:
                linked_expense.delete()

        if status_changed:
            if instance.status == Rental.Status.ACTIVE:
                instance.other_expenses.filter(
                    status=OtherExpense.Status.PLANNED,
                ).update(status=OtherExpense.Status.IN_PROGRESS)
                Vehicle.objects.filter(
                    pk=instance.vehicle_id,
                ).update(status=Vehicle.Status.RENTED)
            elif instance.status == Rental.Status.COMPLETED:
                instance.other_expenses.filter(
                    status=OtherExpense.Status.IN_PROGRESS,
                ).update(status=OtherExpense.Status.COMPLETED)
                Vehicle.objects.filter(
                    pk=instance.vehicle_id,
                ).update(status=Vehicle.Status.AVAILABLE)

    instance._previous_status = instance.status
    instance._previous_additional_fee = instance.additional_fee
    instance._previous_additional_fee_description = instance.additional_fee_description
