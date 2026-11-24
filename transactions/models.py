
from django.db import models
from django.conf import settings

from deposits.models import Account


class Transaction(models.Model):

    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('INTEREST', 'Interest Credit'),
        ('REVERSAL', 'Reversal'),
        ('LOAN_DISBURSEMENT', 'Loan Disbursement'),
        ('LOAN_REPAYMENT', 'Loan Repayment'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('POSTED', 'Posted'),
        ('REVERSED', 'Reversed'),
    ]

    transaction_number = models.CharField(
        max_length=30,
        unique=True
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='transactions',
        null=True,
        blank=True
    )

    loan_payment = models.OneToOneField(
        'loans.LoanPayment',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ledger_transaction'
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_number} - {self.transaction_type}"

    class Meta:
        ordering = ['-created_at']

        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='transaction_amount_positive'
            )
        ]
