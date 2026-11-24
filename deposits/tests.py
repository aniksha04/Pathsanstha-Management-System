from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from branches.models import Branch
from accounts.models import StaffProfile
from members.models import Member
from deposits.models import Account, AccountType
from deposits.services import deposit_money, withdraw_money
from transactions.models import Transaction


class DepositAccountTest(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            branch_name="Main Branch", branch_code="BR001", address="Kolhapur", phone="9876543210"
        )
        self.acc_type = AccountType.objects.create(
            name="SAVINGS", interest_rate=Decimal("4.00"), minimum_balance=Decimal("500.00")
        )

        self.accountant = User.objects.create_user(username="acc_staff", password="password")
        StaffProfile.objects.create(user=self.accountant, role="ACCOUNTANT", branch=self.branch)

        self.member = Member.objects.create(
            member_number="MEM100", full_name="Test Holder", date_of_birth=date(1995, 5, 5),
            gender="MALE", phone="9123456789", address="Address", branch=self.branch, status="ACTIVE"
        )

        self.account = Account.objects.create(
            account_number="ACC100", member=self.member, account_type=self.acc_type,
            branch=self.branch, opening_balance=Decimal("1000.00"), current_balance=Decimal("1000.00"), status="ACTIVE"
        )

    def test_deposit_money(self):
        txn = deposit_money(self.account.id, Decimal("500.00"), self.accountant)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal("1500.00"))
        self.assertEqual(txn.amount, Decimal("500.00"))
        self.assertEqual(txn.transaction_type, "DEPOSIT")

    def test_withdraw_money_success(self):
        txn = withdraw_money(self.account.id, Decimal("300.00"), self.accountant)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal("700.00"))
        self.assertEqual(txn.transaction_type, "WITHDRAWAL")

    def test_withdraw_insufficient_funds_fails(self):
        with self.assertRaises(Exception):
            withdraw_money(self.account.id, Decimal("5000.00"), self.accountant)
        self.account.refresh_from_db()
        self.assertEqual(self.account.current_balance, Decimal("1000.00"))
