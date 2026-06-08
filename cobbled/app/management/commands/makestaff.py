import re
from argparse import ArgumentParser, ArgumentTypeError
from typing import Unpack

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

RE_EMAIL = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def email_type(value: str) -> str:
    """
    Checks a string is an email addresses.

    :param value: The string to check.
    :raises ArgumentTypeError: If it's not a valid email address.
    :return: The string, if it's correct.
    """
    if not RE_EMAIL.match(value):
        raise ArgumentTypeError(f"'{value}' is not a valid email")
    return value


class Command(BaseCommand):
    """
    Management command that makes a given user account an active member of staff.
    """

    help = "Registers a given email as staff for the site."

    def add_arguments(self, parser: ArgumentParser):
        """
        Adds the positional argument for email, and flag for superuser status.

        :param parser: The argument parser object.
        """
        parser.add_argument(
            "email",
            type=email_type,
            help="The email of the google account to register as staff for the site. They must already have logged in once.",
        )
        parser.add_argument(
            "--superuser",
            "-s",
            action="store_true",
            help="Whether to make the user a full superuser.",
        )

    def handle(self, *args: str, **options: Unpack[str | bool]):
        if "email" not in options:
            raise CommandError("No email provided")

        try:
            user = get_user_model().objects.get(email=options["email"])
            user.is_staff = True
            user.is_active = True
            user.is_superuser = options.get("superuser", False)
            user.save()

            if user.is_superuser:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Registered user with email '{options['email']}' as superuser"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"Registered user with email '{options['email']}' as staff")
                )

        except get_user_model().DoesNotExist:
            raise CommandError(f"No user found with email '{options['email']}'")
