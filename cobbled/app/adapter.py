from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.http import HttpRequest

from app.models.researcher import Researcher

User = get_user_model()


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
        user.is_active = False
        user.save()
        researcher: Researcher = Researcher(user=user)
        researcher.save()
        return user

    def get_connect_redirect_url(self, request: HttpRequest, socialaccount) -> str:
        """
        Gets the URL to go to after connecting a social account

        :param request: The signup request.
        :param socialacccount: The AllAuth social account link.
        :returns: The URL to redirect to.
        """
        return "/inactive/"
