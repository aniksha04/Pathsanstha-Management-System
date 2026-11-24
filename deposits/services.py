
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Account
from transactions.models import Transaction
from loans.permissions import is_accountant


def check_account_branch_access(account, user):

    if user.is_superuser:
        return

    try:
        profile = user.staffprofile
    except Exception:
        raise PermissionError("Staff profile not found.")

    if profile.role == 'ADMIN':
        return

    if profile.branch_id != account.branch_id:
        raise PermissionError(
            "You are not authorized to access this branch's account."
        )


@transaction.atomic
def deposit_money(account_id, amount, user):

    if not is_accountant(user):
        raise PermissionError(
            "You are not authorized to deposit money."
        )

    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValidationError("Deposit amount must be greater than zero.")

    account = Account.objects.select_for_update().get(id=account_id)

    check_account_branch_access(account, user)

    if account.status != 'ACTIVE':
        raise ValidationError("Account is not active.")

    account.current_balance += amount
    account.save(update_fields=['current_balance'])

    transaction_number = (
        f"DEP-{account.account_number}-"
        f"{Transaction.objects.count() + 1:06d}"
    )

    deposit = Transaction.objects.create(
        transaction_number=transaction_number,
        account=account,
        transaction_type='DEPOSIT',
        amount=amount,
        description='Cash deposit',
        created_by=user,
        status='POSTED'
    )

    return deposit


@transaction.atomic
def withdraw_money(account_id, amount, user):

    if not is_accountant(user):
        raise PermissionError(
            "You are not authorized to withdraw money."
        )

    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValidationError("Withdrawal amount must be greater than zero.")

    account = Account.objects.select_for_update().get(id=account_id)

    check_account_branch_access(account, user)

    if account.status != 'ACTIVE':
        raise ValidationError("Account is not active.")

    if account.current_balance < amount:
        raise ValidationError("Insufficient account balance.")

    account.current_balance -= amount
    account.save(update_fields=['current_balance'])

    transaction_number = (
        f"WDR-{account.account_number}-"
        f"{Transaction.objects.count() + 1:06d}"
    )

    withdrawal = Transaction.objects.create(
        transaction_number=transaction_number,
        account=account,
        transaction_type='WITHDRAWAL',
        amount=amount,
        description='Cash withdrawal',
        created_by=user,
        status='POSTED'
    )

    return withdrawal
