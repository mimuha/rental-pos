from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Rental, OtherExpense, ExpenseType, Vehicle

EXPENSE_TYPE_NAME = 'Biaya Operasional Perjalanan'
_UNSET = object()


def _get_expense_type():
    expense_type, _ = ExpenseType.objects.get_or_create(
        name=EXPENSE_TYPE_NAME,
        defaults={'description': 'Biaya operasional terkait perjalanan rental'},
    )
    return expense_type


def _get_linked_expense(instance, expense_type):
    return instance.other_expenses.filter(expense_type=expense_type).first()


def _build_description(instance):
    return instance.additional_fee_description or f'Biaya tambahan order {instance.invoice_number} ({instance.customer.full_name})'


def _sync_status(instance):
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


def _should_sync(update_fields, field_name):
    return update_fields is None or field_name in update_fields


@receiver(pre_save, sender=Rental)
def capture_rental_previous_state(sender, instance, **kwargs):
    previous = None
    if instance.pk:
        previous = sender.objects.filter(pk=instance.pk).values(
            'status',
            'additional_fee',
            'additional_fee_description',
        ).first()

    if previous is None:
        instance._db_previous_status = _UNSET
        instance._db_previous_additional_fee = _UNSET
        instance._db_previous_additional_fee_description = _UNSET
        return

    instance._db_previous_status = previous['status']
    instance._db_previous_additional_fee = previous['additional_fee']
    instance._db_previous_additional_fee_description = previous['additional_fee_description']


@receiver(post_save, sender=Rental)
def handle_rental_other_expenses(sender, instance, created, **kwargs):
    raw_update_fields = kwargs.get('update_fields')
    update_fields = None if raw_update_fields is None else set(raw_update_fields)

    previous_status = getattr(instance, '_db_previous_status', _UNSET)
    previous_fee = getattr(instance, '_db_previous_additional_fee', _UNSET)
    previous_desc = getattr(instance, '_db_previous_additional_fee_description', _UNSET)

    fee_changed = (
        _should_sync(update_fields, 'additional_fee')
        and previous_fee is not _UNSET
        and previous_fee != instance.additional_fee
    )
    desc_changed = (
        _should_sync(update_fields, 'additional_fee_description')
        and previous_desc is not _UNSET
        and previous_desc != instance.additional_fee_description
    )
    status_changed = (
        _should_sync(update_fields, 'status')
        and previous_status is not _UNSET
        and previous_status != instance.status
    )

    if created:
        if instance.additional_fee > 0:
            expense_type = _get_expense_type()
            OtherExpense.objects.create(
                rental=instance,
                expense_type=expense_type,
                expense_date=instance.start_at or timezone.now(),
                description=_build_description(instance),
                total_cost=instance.additional_fee,
                status=OtherExpense.Status.PLANNED,
                reference_number=f'dari {instance.invoice_number} ({instance.customer.full_name})',
                payee=instance.customer.full_name,
            )
        _sync_status(instance)
        return

    if fee_changed or desc_changed:
        expense_type = _get_expense_type()
        linked_expense = _get_linked_expense(instance, expense_type)
        description = _build_description(instance)

        if instance.additional_fee > 0:
            if linked_expense:
                linked_update_fields = []
                if fee_changed:
                    linked_expense.total_cost = instance.additional_fee
                    linked_update_fields.append('total_cost')
                if desc_changed:
                    linked_expense.description = description
                    linked_update_fields.append('description')
                if not linked_expense.payee:
                    linked_expense.payee = instance.customer.full_name
                    linked_update_fields.append('payee')
                if linked_update_fields:
                    linked_update_fields.append('updated_at')
                    linked_expense.save(update_fields=linked_update_fields)
            else:
                OtherExpense.objects.create(
                    rental=instance,
                    expense_type=expense_type,
                    expense_date=instance.start_at or timezone.now(),
                    description=description,
                    total_cost=instance.additional_fee,
                    status=OtherExpense.Status.PLANNED,
                    reference_number=f'dari {instance.invoice_number} ({instance.customer.full_name})',
                    payee=instance.customer.full_name,
                )
        elif linked_expense:
            linked_expense.delete()

    if status_changed:
        _sync_status(instance)
