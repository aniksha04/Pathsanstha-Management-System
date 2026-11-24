
from django.db import models
from members.models import Member
from branches.models import Branch
from django.conf import settings


class LoanProduct(models.Model):

    INTEREST_METHODS = [
        ('FLAT', 'Flat Rate'),
        ('REDUCING', 'Reducing Balance'),
    ]

    loan_name = models.CharField(max_length=100)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_tenure_months = models.PositiveIntegerField()

    interest_method = models.CharField(
        max_length=10,
        choices=INTEREST_METHODS
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.loan_name


class Loan(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('DISBURSED', 'Disbursed'),
        ('CLOSED', 'Closed'),
    ]

    loan_number = models.CharField(max_length=30, unique=True)

    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name='loans'
    )

    loan_product = models.ForeignKey(
        LoanProduct,
        on_delete=models.PROTECT
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT
    )

    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tenure_months = models.PositiveIntegerField()

    outstanding_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    applied_at = models.DateTimeField(auto_now_add=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    approved_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    def __str__(self):
        return self.loan_number


class LoanRepayment(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
    ]

    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name='repayments'
    )

    installment_number = models.PositiveIntegerField()
    due_date = models.DateField()

    principal_due = models.DecimalField(max_digits=12, decimal_places=2)
    interest_due = models.DecimalField(max_digits=12, decimal_places=2)
    total_due = models.DecimalField(max_digits=12, decimal_places=2)

    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Track principal and interest paid separately
    principal_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    interest_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    class Meta:
        ordering = ['due_date']
        constraints = [
            models.UniqueConstraint(
                fields=['loan', 'installment_number'],
                name='unique_loan_installment'
            )
        ]

    def __str__(self):
        return f"{self.loan.loan_number} - EMI {self.installment_number}"


class LoanPayment(models.Model):

    PAYMENT_MODES = [
        ('CASH', 'Cash'),
        ('UPI', 'UPI'),
        ('BANK', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
    ]

    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name='payments'
    )

    repayment = models.ForeignKey(
        LoanRepayment,
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True
    )

    receipt_number = models.CharField(max_length=30, unique=True)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    payment_date = models.DateTimeField(auto_now_add=True)

    payment_mode = models.CharField(
        max_length=10,
        choices=PAYMENT_MODES
    )

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    def __str__(self):
        return self.receipt_number

