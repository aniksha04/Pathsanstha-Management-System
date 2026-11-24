from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from branches.models import Branch
from accounts.models import StaffProfile
from accounts.permissions import (
    is_admin, is_manager, is_accountant,
    can_manage_members, can_manage_branches, can_manage_staff,
    get_user_role, get_user_branch
)


class RBACPermissionsTest(TestCase):
    def setUp(self):
        self.branch1 = Branch.objects.create(
            branch_name="Head Office",
            branch_code="BR001",
            address="Kolhapur",
            phone="9876543210"
        )
        self.branch2 = Branch.objects.create(
            branch_name="Branch Two",
            branch_code="BR002",
            address="Satara",
            phone="9876543211"
        )

        # Admin User
        self.admin_user = User.objects.create_user(username="admin_test", password="password123")
        StaffProfile.objects.create(user=self.admin_user, role="ADMIN")

        # Manager User (Branch 1)
        self.mgr_user = User.objects.create_user(username="mgr_test", password="password123")
        StaffProfile.objects.create(user=self.mgr_user, role="MANAGER", branch=self.branch1)

        # Accountant User (Branch 1)
        self.acc_user = User.objects.create_user(username="acc_test", password="password123")
        StaffProfile.objects.create(user=self.acc_user, role="ACCOUNTANT", branch=self.branch1)

    def test_permission_helpers(self):
        # Admin checks
        self.assertTrue(is_admin(self.admin_user))
        self.assertTrue(is_manager(self.admin_user))
        self.assertTrue(is_accountant(self.admin_user))
        self.assertTrue(can_manage_branches(self.admin_user))
        self.assertTrue(can_manage_staff(self.admin_user))
        self.assertTrue(can_manage_members(self.admin_user))
        self.assertEqual(get_user_role(self.admin_user), "ADMIN")

        # Manager checks
        self.assertFalse(is_admin(self.mgr_user))
        self.assertTrue(is_manager(self.mgr_user))
        self.assertTrue(is_accountant(self.mgr_user))
        self.assertFalse(can_manage_branches(self.mgr_user))
        self.assertFalse(can_manage_staff(self.mgr_user))
        self.assertTrue(can_manage_members(self.mgr_user))
        self.assertEqual(get_user_role(self.mgr_user), "MANAGER")
        self.assertEqual(get_user_branch(self.mgr_user), self.branch1)

        # Accountant checks
        self.assertFalse(is_admin(self.acc_user))
        self.assertFalse(is_manager(self.acc_user))
        self.assertTrue(is_accountant(self.acc_user))
        self.assertFalse(can_manage_branches(self.acc_user))
        self.assertFalse(can_manage_staff(self.acc_user))
        self.assertFalse(can_manage_members(self.acc_user))
        self.assertEqual(get_user_role(self.acc_user), "ACCOUNTANT")
        self.assertEqual(get_user_branch(self.acc_user), self.branch1)

    def test_login_and_logout(self):
        client = Client()
        response = client.post(reverse('login'), {'username': 'mgr_test', 'password': 'password123'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))

        # Logout
        response = client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))
