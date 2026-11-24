from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from branches.models import Branch
from accounts.models import StaffProfile
from members.models import Member
from deposits.models import Account, AccountType
from loans.models import Loan, LoanProduct


class DashboardReportsTest(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            branch_name="Main Branch", branch_code="BR001", address="Kolhapur", phone="9876543210"
        )
        self.acc_type = AccountType.objects.create(
            name="SAVINGS", interest_rate=Decimal("4.00"), minimum_balance=Decimal("0.00")
        )

        self.admin = User.objects.create_user(username="admin_rep", password="password")
        StaffProfile.objects.create(user=self.admin, role="ADMIN")

        self.accountant = User.objects.create_user(username="acc_rep", password="password")
        StaffProfile.objects.create(user=self.accountant, role="ACCOUNTANT", branch=self.branch)

        self.member = Member.objects.create(
            member_number="MEM200", full_name="Report Member", date_of_birth=date(1992, 1, 1),
            gender="FEMALE", phone="9888877777", address="Kolhapur", branch=self.branch, status="ACTIVE"
        )

        self.account = Account.objects.create(
            account_number="ACC200", member=self.member, account_type=self.acc_type,
            branch=self.branch, opening_balance=Decimal("25000.00"), current_balance=Decimal("25000.00"), status="ACTIVE"
        )

    def test_dashboard_authenticated(self):
        client = Client()
        client.login(username="admin_rep", password="password")
        response = client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Available Savings Balance")
        self.assertContains(response, "25000.00")
        self.assertContains(response, "Branch-Wise Financial Overview")

    def test_loan_summary_view(self):
        client = Client()
        client.login(username="acc_rep", password="password")
        response = client.get(reverse('loan_summary'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cooperative Credit Portfolio Summary")
