from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class UserAdminTestCase(TestCase):
    def setUp(self):
        # Create an admin user to make requests
        self.admin = User.objects.create_superuser(
            username="adminuser",
            email="admin@example.com",
            password="adminpassword"
        )
        # Create a test user to edit
        self.test_user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="originalpassword",
            first_name="OriginalFirst",
            last_name="OriginalLast",
            is_active=True
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_get_user_edit_page(self):
        url = f"/iommi_admin/auth/user/{self.test_user.pk}/edit/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Ensure the prefilled password field is empty (not showing the hashed password)
        self.assertContains(response, 'value=""', html=False)

    def test_edit_user_without_password(self):
        url = f"/iommi_admin/auth/user/{self.test_user.pk}/edit/"
        # Submit the edit form with updated names but empty password
        data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "first_name": "UpdatedFirst",
            "last_name": "UpdatedLast",
            "is_active": "on",
            "password": "",
            "-submit": ""  # iommi submit button marker
        }
        response = self.client.post(url, data=data)
        # iommi redirects back after successful edit
        self.assertEqual(response.status_code, 302)

        # Refresh from database
        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.first_name, "UpdatedFirst")
        self.assertEqual(self.test_user.last_name, "UpdatedLast")
        self.assertTrue(self.test_user.is_active)

        # Verify the original password was preserved
        check_client = Client()
        login_success = check_client.login(username="testuser", password="originalpassword")
        self.assertTrue(login_success)

    def test_edit_user_with_new_password(self):
        url = f"/iommi_admin/auth/user/{self.test_user.pk}/edit/"
        # Submit the edit form with updated names and a new password
        data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "first_name": "UpdatedFirst",
            "last_name": "UpdatedLast",
            "is_active": "on",
            "password": "brandnewpassword",
            "-submit": ""
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 302)

        # Refresh from database
        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.first_name, "UpdatedFirst")
        self.assertEqual(self.test_user.last_name, "UpdatedLast")
        self.assertTrue(self.test_user.is_active)

        # Verify the original password no longer works, and the new one does
        check_client = Client()
        login_old_failed = check_client.login(username="testuser", password="originalpassword")
        self.assertFalse(login_old_failed)
        login_new_success = check_client.login(username="testuser", password="brandnewpassword")
        self.assertTrue(login_new_success)
