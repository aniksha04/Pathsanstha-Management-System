from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from branches.models import Branch
from accounts.models import StaffProfile
from members.models import Member
from deposits.models import Account, AccountType
from loans.models import Loan, LoanProduct, LoanRepayment, LoanPayment
from loans.services import (
    calculate_emi,
    apply_for_loan,
    approve_loan,
    disburse_loan,
    generate_emi_schedule,
    collect_emi_payment,
    add_months
)


class LoanServiceWorkflowTest(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            branch_name="Main Branch", branch_code="BR001", address="Kolhapur", phone="9876543210"
        )
        self.acc_type = AccountType.objects.create(
            name="SAVINGS", interest_rate=Decimal("4.00"), minimum_balance=Decimal("0.00")
        )

        self.manager = User.objects.create_user(username="mgr_user", password="password")
        StaffProfile.objects.create(user=self.manager, role="MANAGER", branch=self.branch)

        self.accountant = User.objects.create_user(username="acc_user", password="password")
        StaffProfile.objects.create(user=self.accountant, role="ACCOUNTANT", branch=self.branch)

        self.member = Member.objects.create(
            member_number="MEM010", full_name="Borrower Member", date_of_birth=date(1990, 1, 1),
            gender="MALE", phone="9999988888", address="Town", branch=self.branch, status="ACTIVE"
        )

        self.savings_account = Account.objects.create(
            account_number="ACC010", member=self.member, account_type=self.acc_type,
            branch=self.branch, opening_balance=Decimal("1000.00"), current_balance=Decimal("1000.00"), status="ACTIVE"
        )

        self.product_reducing = LoanProduct.objects.create(
            loan_name="Personal Loan",
            interest_rate=Decimal("12.00"),
            min_amount=Decimal("1000.00"),
            max_amount=Decimal("100000.00"),
            max_tenure_months=12,
            interest_method="REDUCING"
        )

        self.product_flat = LoanProduct.objects.create(
            loan_name="Gold Loan",
            interest_rate=Decimal("10.00"),
            min_amount=Decimal("1000.00"),
            max_amount=Decimal("100000.00"),
            max_tenure_months=12,
            interest_method="FLAT"
        )

    def test_calculate_emi(self):
        # 10,000 at 12% reducing for 6 months
        emi_reducing = calculate_emi(Decimal("10000.00"), Decimal("12.00"), 6, method="REDUCING")
        self.assertEqual(emi_reducing, Decimal("1725.48"))

        # 10,000 at 10% flat for 12 months -> Interest = 1000, Total = 11000, EMI = 11000/12 = 916.67
        emi_flat = calculate_emi(Decimal("10000.00"), Decimal("10.00"), 12, method="FLAT")
        self.assertEqual(emi_flat, Decimal("916.67"))

    def test_complete_loan_lifecycle(self):
        # 1. Apply for loan
        loan = apply_for_loan(
            member=self.member,
            loan_product=self.product_reducing,
            principal_amount=Decimal("10000.00"),
            tenure_months=6,
            staff_user=self.manager
        )
        self.assertEqual(loan.status, "PENDING")
        self.assertEqual(loan.principal_amount, Decimal("10000.00"))

        # 2. Approve loan
        approve_loan(loan, self.manager)
        loan.refresh_from_db()
        self.assertEqual(loan.status, "APPROVED")
        self.assertEqual(loan.approved_by, self.manager)

        # 3. Disburse loan (funds credited to savings account)
        disburse_loan(loan, self.manager)
        loan.refresh_from_db()
        self.savings_account.refresh_from_db()

        self.assertEqual(loan.status, "DISBURSED")
        self.assertEqual(loan.outstanding_balance, Decimal("10000.00"))
        # Savings account was 1000, now should be 11000!
        self.assertEqual(self.savings_account.current_balance, Decimal("11000.00"))

        # 4. Generate EMI Schedule
        first_due = add_months(timezone.localdate(), 1)
        schedule = generate_emi_schedule(loan, first_due, self.manager)
        self.assertEqual(len(schedule), 6)
        self.assertEqual(loan.repayments.count(), 6)

        first_installment = loan.repayments.order_by('installment_number').first()
        self.assertEqual(first_installment.status, "PENDING")

        # 5. Collect EMI repayment
        emi_amt = first_installment.total_due
        payment = collect_emi_payment(
            loan=loan,
            repayment=first_installment,
            amount=emi_amt,
            payment_mode="CASH",
            receipt_number="RCP_TEST_001",
            staff_user=self.accountant
        )

        first_installment.refresh_from_db()
        loan.refresh_from_db()

        self.assertEqual(first_installment.status, "PAID")
        self.assertEqual(payment.amount, emi_amt)
        # Outstanding principal should have decreased by principal_paid
        self.assertLess(loan.outstanding_balance, Decimal("10000.00"))
