from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Rental, OtherExpense, ExpenseType

EXPENSE_TYPE_NAME = 'Biaya Operasional Perjalanan'


def _get_expense_type():
    expense_type, _ = ExpenseType.objects.get_or_create(
        name=EXPENSE_TYPE_NAME,
        defaults={'description': 'Biaya operasional terkait perjalanan rental'},
    )
    return expense_type


def _get_linked_expense(instance, expense_type):
    return instance.other_expenses.filter(expense_type=expense_type).first()


@receiver(post_save, sender=Rental)
def handle_rental_other_expenses(sender, instance, created, **kwargs):
    expense_type = _get_expense_type()
    previous_status = getattr(instance, '_previous_status', None)
    status_changed = previous_status is not None and previous_status != instance.status
    previous_fee = getattr(instance, '_previous_additional_fee', None)
    fee_changed = previous_fee is not None and previous_fee != instance.additional_fee
    linked_expense = _get_linked_expense(instance, expense_type)

    if created:
        if instance.additional_fee > 0:
            OtherExpense.objects.create(
                rental=instance,
                expense_type=expense_type,
                expense_date=instance.start_at or timezone.now(),
                description=f'Biaya tambahan order {instance.invoice_number}',
                total_cost=instance.additional_fee,
                status=OtherExpense.Status.PLANNED,
            )
    else:
        if fee_changed:
            if instance.additional_fee > 0:
                if linked_expense:
                    linked_expense.total_cost = instance.additional_fee
                    linked_expense.save(update_fields=['total_cost', 'updated_at'])
                else:
                    OtherExpense.objects.create(
                        rental=instance,
                        expense_type=expense_type,
                        expense_date=instance.start_at or timezone.now(),
                        description=f'Biaya tambahan order {instance.invoice_number}',
                        total_cost=instance.additional_fee,
                        status=OtherExpense.Status.PLANNED,
                    )
            elif linked_expense:
                linked_expense.delete()

        if status_changed:
            if instance.status == Rental.Status.ACTIVE:
                instance.other_expenses.filter(
                    status=OtherExpense.Status.PLANNED,
                ).update(status=OtherExpense.Status.IN_PROGRESS)
            elif instance.status == Rental.Status.COMPLETED:
                instance.other_expenses.filter(
                    status=OtherExpense.Status.IN_PROGRESS,
                ).update(status=OtherExpense.Status.COMPLETED)

    instance._previous_status = instance.status
    instance._previous_additional_fee = instance.additional_fee
