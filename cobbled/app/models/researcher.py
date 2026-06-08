from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import CASCADE, CharField, Model, OneToOneField, TextField
from rules import add_perm, is_active, is_staff, predicate


def validate_orcid_format(value: str):
    """
    Validates an input ORCID to make sure it fits the format.

    :param value: The text entered for the ORCID.
    :raises ValidationError: If not formatted correctly.
    """
    try:
        # 0123[4]5678[9]ABCD[E]FGHI
        # 0000-0000-0000-0000

        if value[4] != "-" or value[9] != "-" or value[14] != "-":
            raise ValidationError(
                "ORCID must be in the format 0000-0000-1234-5678. Did you forget the dashes?"
            )

        int(value[:4]) and int(value[5:9]) and int(value[10:14]) and int(value[15:])

    except ValueError:
        raise ValidationError("ORCID must be in the format 0000-0000-1234-5689")


class Researcher(Model):
    """
    Researcher class that extends user class
    """

    user = OneToOneField(get_user_model(), primary_key=True, on_delete=CASCADE)
    affiliations = TextField(
        null=False,
        blank=False,
        help_text="Primary affiliation or list of affiliations suitable for including in BibTex.",
    )
    orcid = CharField(
        max_length=32,
        null=False,
        blank=False,
        verbose_name="ORCID",
        help_text="In the format 0000-0000-1234-5689.",
        validators=[validate_orcid_format],
    )

    def get_absolute_url(self) -> str:
        """
        Gets the absolute url for the researcher.
        """
        return f"/researcher/{self.pk}/"

    def __str__(self) -> str:
        return f"{self.user.get_full_name()}"

    def __repr__(self) -> str:
        return f"{self.user.get_full_name()}"


User = get_user_model()


@predicate
def is_researcher(user: User, researcher: Researcher) -> bool:
    """
    Does this user account correspond to this researcher?

    :param user: User to check.
    :param researcher: The researcher to check.
    :return: True if the user is this Researcher, or false otherwise.
    """
    return user and user.researcher == researcher


# Rules for database interactions with this source
# Conditions are tested on the user wanting to make the change
add_perm("app.change_researcher", is_researcher | is_staff)
add_perm("app.view_researcher", is_active)
