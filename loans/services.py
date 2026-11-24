
import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.db import transaction
from django.utils import timezone

from accounts.models import StaffProfile
from deposits.models import Account
from transactions.models import Transaction

from .models import Loan, LoanRepayment, LoanPayment
from .permissions import is_manager, is_accountant


# --------------------------------------------------
# COMMON HELPERS
# --------------------------------------------------

def get_staff_profile(user):
    try:
        return user.staffprofile
    except (StaffProfile.DoesNotExist, AttributeError):
        return None


def is_global_admin(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return StaffProfile.objects.filter(
        user=user,
        role="ADMIN"
    ).exists()


def check_branch_access(user, loan):
    """
    Admin can access all loans.
    Managers and Accountants can access only their own branch.
    """

    if is_global_admin(user):
        return True

    profile = get_staff_profile(user)

    if not profile or not profile.branch_id:
        raise PermissionError("Your staff account has no assigned branch.")

    if loan.branch_id != profile.branch_id:
        raise PermissionError(
            "You cannot access loans belonging to another branch."
        )

    return True


def convert_to_decimal(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Please enter a valid amount.")

    if not amount.is_finite():
        raise ValueError("Amount must be a valid number.")

    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# --------------------------------------------------
# EMI CALCULATION
# --------------------------------------------------

def calculate_emi(principal, annual_rate, tenure_months, method="REDUCING"):
    principal = convert_to_decimal(principal)
    annual_rate = Decimal(str(annual_rate))
    tenure_months = int(tenure_months)

    if principal <= 0:
        raise ValueError("Principal amount must be greater than zero.")

    if annual_rate < 0:
        raise ValueError("Interest rate cannot be negative.")

    if tenure_months <= 0:
        raise ValueError("Tenure must be greater than zero.")

    monthly_rate = annual_rate / Decimal("1200")

    if method == "FLAT":
        total_interest = (
            principal * annual_rate * tenure_months
        ) / Decimal("1200")

        emi = (principal + total_interest) / tenure_months

    elif method == "REDUCING":

        if monthly_rate == 0:
            emi = principal / tenure_months

        else:
            factor = (1 + monthly_rate) ** tenure_months

            emi = (
                principal * monthly_rate * factor
            ) / (factor - 1)

    else:
        raise ValueError("Invalid interest calculation method.")

    return emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# --------------------------------------------------
# DATE HELPER
# --------------------------------------------------

def add_months(original_date, months):
    month = original_date.month - 1 + months

    year = original_date.year + month // 12
    month = month % 12 + 1

    day = min(
        original_date.day,
        calendar.monthrange(year, month)[1]
    )

    return date(year, month, day)


# --------------------------------------------------
# GENERATE EMI SCHEDULE
# --------------------------------------------------

@transaction.atomic
def generate_emi_schedule(loan, first_due_date, staff_user):

    loan = Loan.objects.select_for_update().get(pk=loan.pk)

    if not is_manager(staff_user):
        raise PermissionError(
            "Only Managers or Admins can generate EMI schedules."
        )

    check_branch_access(staff_user, loan)

    if loan.status != "DISBURSED":
        raise ValueError(
            "EMI schedule can only be generated for disbursed loans."
        )

    if loan.repayments.exists():
        raise ValueError("EMI schedule already exists.")

    if first_due_date < timezone.localdate():
        raise ValueError("First due date cannot be in the past.")

    principal = convert_to_decimal(loan.principal_amount)
    annual_rate = Decimal(str(loan.interest_rate))
    tenure = int(loan.tenure_months)

    if tenure <= 0:
        raise ValueError("Loan tenure must be greater than zero.")

    method = loan.loan_product.interest_method

    emi = calculate_emi(
        principal,
        annual_rate,
        tenure,
        method
    )

    monthly_rate = annual_rate / Decimal("1200")
    remaining_principal = principal

    repayments = []

    for installment_number in range(1, tenure + 1):

        due_date = add_months(
            first_due_date,
            installment_number - 1
        )

        if method == "FLAT":

            principal_due = (
                principal / Decimal(tenure)
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            interest_due = (
                principal * annual_rate / Decimal("1200")
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

        else:

            interest_due = (
                remaining_principal * monthly_rate
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            principal_due = emi - interest_due

        # Adjust the final installment to clear
        # any rounding difference.
        if installment_number == tenure:
            principal_due = remaining_principal

        principal_due = min(principal_due, remaining_principal)

        total_due = principal_due + interest_due

        repayments.append(
            LoanRepayment(
                loan=loan,
                installment_number=installment_number,
                due_date=due_date,
                principal_due=principal_due,
                interest_due=interest_due,
                total_due=total_due,
                amount_paid=Decimal("0.00"),
                principal_paid=Decimal("0.00"),
                interest_paid=Decimal("0.00"),
                status="PENDING"
            )
        )

        remaining_principal -= principal_due

    LoanRepayment.objects.bulk_create(repayments)

    return repayments


# --------------------------------------------------
# APPROVE LOAN
# --------------------------------------------------

@transaction.atomic
def approve_loan(loan, manager):

    loan = Loan.objects.select_for_update().get(pk=loan.pk)

    if not is_manager(manager):
        raise PermissionError(
            "Only Managers or Admins can approve loans."
        )

    check_branch_access(manager, loan)

    if loan.status != "PENDING":
        raise ValueError("Only pending loans can be approved.")

    loan.status = "APPROVED"
    loan.approved_by = manager
    loan.approved_at = timezone.now()

    loan.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at"
        ]
    )

    return loan


# --------------------------------------------------
# DISBURSE LOAN
# --------------------------------------------------

@transaction.atomic
def disburse_loan(loan, staff_user):

    loan = Loan.objects.select_for_update().get(pk=loan.pk)

    if not is_manager(staff_user):
        raise PermissionError(
            "Only Managers or Admins can disburse loans."
        )

    check_branch_access(staff_user, loan)

    if loan.status != "APPROVED":
        raise ValueError("Only approved loans can be disbursed.")

    account = Account.objects.select_for_update().filter(
        member=loan.member,
        branch=loan.branch,
        status="ACTIVE"
    ).first()

    if not account:
        raise ValueError(
            "No active account found for this member in the loan branch."
        )

    principal = convert_to_decimal(loan.principal_amount)

    if principal <= 0:
        raise ValueError("Loan amount must be greater than zero.")

    # Credit the loan amount to the member's account.
    account.current_balance += principal
    account.save(update_fields=["current_balance"])

    # Create the loan disbursement ledger transaction.
    Transaction.objects.create(
        transaction_number=f"LD-{loan.loan_number}",
        account=account,
        transaction_type="LOAN_DISBURSEMENT",
        amount=principal,
        description=f"Loan disbursement for {loan.loan_number}",
        created_by=staff_user,
        status="POSTED"
    )

    loan.status = "DISBURSED"
    loan.outstanding_balance = principal

    loan.save(
        update_fields=[
            "status",
            "outstanding_balance"
        ]
    )

    return loan


# --------------------------------------------------
# COLLECT EMI PAYMENT
# --------------------------------------------------

@transaction.atomic
def collect_emi_payment(
    loan,
    repayment,
    amount,
    payment_mode,
    receipt_number,
    staff_user
):

    loan = Loan.objects.select_for_update().get(pk=loan.pk)

    if not is_accountant(staff_user):
        raise PermissionError(
            "Only Accountants, Managers or Admins can collect EMI payments."
        )

    check_branch_access(staff_user, loan)

    if loan.status != "DISBURSED":
        raise ValueError("Payments can only be collected for disbursed loans.")

    repayment = LoanRepayment.objects.select_for_update().get(
        pk=repayment.pk,
        loan=loan
    )

    if repayment.status == "PAID":
        raise ValueError("This installment is already paid.")

    amount = convert_to_decimal(amount)

    if amount <= 0:
        raise ValueError("Payment must be greater than zero.")

    remaining_due = (
        repayment.total_due - repayment.amount_paid
    )

    if amount > remaining_due:
        raise ValueError(
            "Payment cannot exceed the remaining installment amount."
        )

    valid_payment_modes = [
        "CASH",
        "UPI",
        "BANK",
        "CHEQUE"
    ]

    if payment_mode not in valid_payment_modes:
        raise ValueError("Invalid payment mode.")

    receipt_number = str(receipt_number).strip()

    if not receipt_number:
        raise ValueError("Receipt number is required.")

    if LoanPayment.objects.filter(
        receipt_number=receipt_number
    ).exists():
        raise ValueError("This receipt number already exists.")

    # Allocate payment to interest first, then principal.
    remaining_interest = (
        repayment.interest_due - repayment.interest_paid
    )

    interest_paid_now = min(amount, remaining_interest)

    principal_paid_now = amount - interest_paid_now

    remaining_principal_due = (
        repayment.principal_due - repayment.principal_paid
    )

    if principal_paid_now > remaining_principal_due:
        raise ValueError("Invalid principal payment allocation.")

    repayment.interest_paid += interest_paid_now
    repayment.principal_paid += principal_paid_now
    repayment.amount_paid += amount

    if repayment.amount_paid == repayment.total_due:
        repayment.status = "PAID"
    else:
        repayment.status = "PARTIAL"

    repayment.save(
        update_fields=[
            "interest_paid",
            "principal_paid",
            "amount_paid",
            "status"
        ]
    )

    # Create payment receipt.
    payment = LoanPayment.objects.create(
        loan=loan,
        repayment=repayment,
        receipt_number=receipt_number,
        amount=amount,
        payment_mode=payment_mode,
        received_by=staff_user
    )

    # Create corresponding ledger transaction.
    Transaction.objects.create(
        transaction_number=f"LR-{receipt_number}",
        account=None,
        loan_payment=payment,
        transaction_type="LOAN_REPAYMENT",
        amount=amount,
        description=f"EMI payment for {loan.loan_number}",
        created_by=staff_user,
        status="POSTED"
    )

    # Reduce outstanding principal only by principal paid.
    loan.outstanding_balance -= principal_paid_now

    if loan.outstanding_balance < 0:
        loan.outstanding_balance = Decimal("0.00")

    if loan.outstanding_balance == 0:
        loan.status = "CLOSED"

    loan.save(
        update_fields=[
            "outstanding_balance",
            "status"
        ]
    )

    return payment


# --------------------------------------------------
# REJECT LOAN
# --------------------------------------------------

@transaction.atomic
def reject_loan(loan, manager):
    loan = Loan.objects.select_for_update().get(pk=loan.pk)

    if not is_manager(manager):
        raise PermissionError("Only Managers or Admins can reject loans.")

    check_branch_access(manager, loan)

    if loan.status != "PENDING":
        raise ValueError("Only pending loans can be rejected.")

    loan.status = "REJECTED"
    loan.approved_by = manager
    loan.approved_at = timezone.now()
    loan.save(update_fields=["status", "approved_by", "approved_at"])
    return loan


# --------------------------------------------------
# APPLY LOAN HELPER
# --------------------------------------------------

def get_next_loan_number():
    last_loan = Loan.objects.order_by('-id').first()
    if last_loan:
        try:
            num = int(''.join(filter(str.isdigit, last_loan.loan_number))) + 1
            return f"LOAN{num:03d}"
        except (ValueError, TypeError):
            return f"LOAN{Loan.objects.count() + 1:03d}"
    return "LOAN001"


@transaction.atomic
def apply_for_loan(member, loan_product, principal_amount, tenure_months, staff_user):
    from accounts.permissions import is_accountant
    if not is_accountant(staff_user):
        raise PermissionError("You are not authorized to create loan applications.")

    if not is_global_admin(staff_user):
        profile = get_staff_profile(staff_user)
        if not profile or profile.branch_id != member.branch_id:
            raise PermissionError("You can only apply for loans for members of your branch.")

    principal = convert_to_decimal(principal_amount)
    tenure = int(tenure_months)

    if principal < loan_product.min_amount or principal > loan_product.max_amount:
        raise ValueError(f"Loan amount must be between ₹{loan_product.min_amount} and ₹{loan_product.max_amount}.")

    if tenure <= 0 or tenure > loan_product.max_tenure_months:
        raise ValueError(f"Loan tenure cannot exceed {loan_product.max_tenure_months} months.")

    loan_number = get_next_loan_number()

    loan = Loan.objects.create(
        loan_number=loan_number,
        member=member,
        loan_product=loan_product,
        branch=member.branch,
        principal_amount=principal,
        interest_rate=loan_product.interest_rate,
        tenure_months=tenure,
        outstanding_balance=Decimal("0.00"),
        status="PENDING"
    )
    return loan

