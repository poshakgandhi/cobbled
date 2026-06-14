from django.test import TestCase
from django.core import mail
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from unittest.mock import patch, MagicMock
from app.adapter import CustomAccountAdapter, UsernameAdapter

User = get_user_model()


class NotificationTestCase(TestCase):
    def setUp(self):
        # Create a superuser to receive notifications
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password123"
        )
        mail.outbox.clear()

    @patch('allauth.account.adapter.DefaultAccountAdapter.save_user')
    def test_notify_inactive_signup(self, mock_save_user):
        user = User(username="newuser", email="newuser@example.com")
        mock_save_user.return_value = user
        
        adapter = CustomAccountAdapter()
        request = HttpRequest()
        saved_user = adapter.save_user(request, user, None, commit=True)
        
        self.assertFalse(saved_user.is_active)
        # Check that an email was sent to the superuser
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "[COBBLED] New User Validation Awaiting")
        self.assertIn("admin@example.com", email.to)
        self.assertIn("newuser", email.body)

    @patch('allauth.account.adapter.DefaultAccountAdapter.save_user')
    def test_no_notify_auto_active_signup(self, mock_save_user):
        user = User(username="poshak", email="poshak.gandhi@soton.ac.uk")
        mock_save_user.return_value = user
        
        adapter = CustomAccountAdapter()
        request = HttpRequest()
        saved_user = adapter.save_user(request, user, None, commit=True)
        
        self.assertTrue(saved_user.is_active)
        # No notification email should be sent for auto-activated users
        self.assertEqual(len(mail.outbox), 0)

    @patch('allauth.socialaccount.adapter.DefaultSocialAccountAdapter.save_user')
    def test_social_signup_notification(self, mock_save_user):
        user = User(username="social_user", email="social@example.com")
        mock_save_user.return_value = user
        
        social_login = MagicMock()
        adapter = UsernameAdapter()
        request = HttpRequest()
        saved_user = adapter.save_user(request, social_login)
        
        self.assertFalse(saved_user.is_active)
        # Check that an email was sent to the superuser
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "[COBBLED] New User Validation Awaiting")
        self.assertIn("admin@example.com", email.to)
