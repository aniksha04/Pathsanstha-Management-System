from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from branches.models import Branch
from accounts.models import StaffProfile
from members.models import Member
from members.form import get_next_member_number


class MemberManagementTest(TestCase):
    def setUp(self):
        self.branch1 = Branch.objects.create(
            branch_name="Main Branch", branch_code="BR001", address="Kolhapur", phone="9876543210"
        )
        self.branch2 = Branch.objects.create(
            branch_name="Branch Two", branch_code="BR002", address="Satara", phone="9876543211"
        )

        self.admin = User.objects.create_user(username="admin_user", password="password")
        StaffProfile.objects.create(user=self.admin, role="ADMIN")

        self.manager1 = User.objects.create_user(username="mgr1", password="password")
        StaffProfile.objects.create(user=self.manager1, role="MANAGER", branch=self.branch1)

        self.accountant1 = User.objects.create_user(username="acc1", password="password")
        StaffProfile.objects.create(user=self.accountant1, role="ACCOUNTANT", branch=self.branch1)

        self.member1 = Member.objects.create(
            member_number="MEM001",
            full_name="Member One",
            date_of_birth=date(1990, 1, 1),
            gender="MALE",
            phone="9000000001",
            address="Kolhapur City",
            branch=self.branch1,
            status="ACTIVE"
        )

    def test_next_member_number_generation(self):
        next_num = get_next_member_number()
        self.assertEqual(next_num, "MEM002")

    def test_manager_member_list_scoped_to_branch(self):
        # Create member in branch 2
        Member.objects.create(
            member_number="MEM002",
            full_name="Member Two",
            date_of_birth=date(1992, 2, 2),
            gender="FEMALE",
            phone="9000000002",
            address="Satara City",
            branch=self.branch2,
            status="ACTIVE"
        )

        client = Client()
        client.login(username="mgr1", password="password")
        response = client.get(reverse('member_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MEM001")
        self.assertNotContains(response, "MEM002")

    def test_accountant_cannot_register_members(self):
        client = Client()
        client.login(username="acc1", password="password")
        response = client.get(reverse('member_register'))
        # Accountant should be redirected
        self.assertEqual(response.status_code, 302)
