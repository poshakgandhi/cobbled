from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.http import HttpRequest

from app.models.researcher import Researcher

User = get_user_model()


def notify_superusers(user: User):
    if not user.is_active:
        from django.core.mail import send_mail
        superusers = User.objects.filter(is_superuser=True)
        recipient_list = [u.email for u in superusers if u.email]
        if recipient_list:
            subject = "[COBBLED] New User Validation Awaiting"
            message = f"A new user has registered and is awaiting validation:\n\nUsername: {user.username}\nEmail: {user.email}\n\nPlease log in and check the Validation Queue to review and approve them."
            send_mail(
                subject,
                message,
                from_email=None,
                recipient_list=recipient_list,
                fail_silently=True,
            )


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Adapter to hook into regular email/password signups.
    """

    def save_user(self, request: HttpRequest, user: User, form, commit: bool = True) -> User:
        """
        Hooks into the user save to create a matching researcher, as well as setting the user to inactive.

        :param request: The signup request.
        :param user: The new user instance.
        :param form: The signup form.
        :param commit: Whether to commit changes immediately.
        :returns: The new user.
        """
        user = super().save_user(request, user, form, commit=False)
        if user.email in ["poshakgandhi@gmail.com", "poshak.gandhi@soton.ac.uk"]:
            user.is_active = True
            user.is_staff = True
            user.is_superuser = True
        else:
            user.is_active = False
        user.save()

        researcher: Researcher = Researcher(
            user=user,
            affiliations="TBD",
            orcid="0000-0000-0000-0000"
        )
        researcher.save()

        notify_superusers(user)
        return user


class UsernameAdapter(DefaultSocialAccountAdapter):
    """ """

    def populate_user(self, request: HttpRequest, sociallogin, data):
        """
        By default, Django uses an account's username in dropdowns e.t.c.
        SocialAccounts use email instead, so we populate the 'username' with the user's name.

        :param request: The signup request.
        :param sociallogin: The AllAuth social account link.
        :param data: The data from the OAuth provider, uses the fields specified in settings.py.
        """
        super().populate_user(request, sociallogin, data)
        sociallogin.user.username = data["email"]

    def save_user(self, request: HttpRequest, sociallogin, form=None) -> User:
        """
        Hooks into the user save to create a matching researcher, as well as setting the user to inactive.

        :param request: The signup request.
        :param sociallogin: The AllAuth social account link.
        :param form: The form, if any, used in account creation (should be None).
        :returns: The new user.
        """
        user: User = super().save_user(request, sociallogin, form)
        if user.email in ["poshakgandhi@gmail.com", "poshak.gandhi@soton.ac.uk"]:
            user.is_active = True
            user.is_staff = True
            user.is_superuser = True
        else:
            user.is_active = False
        user.save()
        researcher: Researcher = Researcher(
            user=user,
            affiliations="TBD",
            orcid="0000-0000-0000-0000"
        )
        researcher.save()
        notify_superusers(user)
        return user

    def get_connect_redirect_url(self, request: HttpRequest, socialaccount) -> str:
        """
        Gets the URL to go to after connecting a social account

        :param request: The signup request.
        :param socialacccount: The AllAuth social account link.
        :returns: The URL to redirect to.
        """
        return "/accounts/inactive/"
