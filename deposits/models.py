
from django.db import models
from django.core.exceptions import ValidationError

from members.models import Member
from branches.models import Branch


class AccountType(models.Model):

    ACCOUNT_CHOICES = [
        ('SAVINGS', 'Savings'),
        ('FIXED', 'Fixed Deposit'),
        ('RECURRING', 'Recurring Deposit'),
    ]

    name = models.CharField(
        max_length=20,
        choices=ACCOUNT_CHOICES,
        unique=True
    )

    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    minimum_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Account(models.Model):

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
        ('FROZEN', 'Frozen'),
    ]

    account_number = models.CharField(
        max_length=20,
        unique=True
    )

    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name='accounts'
    )

    account_type = models.ForeignKey(
        AccountType,
        on_delete=models.PROTECT
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT
    )

    opening_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    opened_at = models.DateField(auto_now_add=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )

    def clean(self):
        super().clean()

        if self.member_id and self.branch_id:
            if self.member.branch_id != self.branch_id:
                raise ValidationError({
                    'branch': (
                        "Account branch must match the member's branch."
                    )
                })

    def save(self, *args, **kwargs):
        if self.member_id and self.branch_id:
            if self.member.branch_id != self.branch_id:
                raise ValidationError(
                    "Account branch must match the member's branch."
                )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.account_number
