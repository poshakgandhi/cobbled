from django.contrib.auth import get_user_model
from django.db.models import (
    RESTRICT,
    BooleanField,
    CharField,
    ForeignKey,
    ManyToManyField,
    Model,
    TextField,
)
from rules import add_perm, is_active, is_staff, predicate

from app.models.researcher import Researcher


class Project(Model):
    """
    Model for a research project.
    """

    name = CharField(
        max_length=128,
        null=False,
        verbose_name="Project Name",
        help_text="The title of the research project.",
    )

    description = TextField(
        null=False,
        help_text="A description of the research project.",
    )

    bibtex = TextField(
        null=True,
        blank=True,
        verbose_name="BibTeX",
        help_text="The formatted Bibtex entry to use when citing this project.",
    )

    principal_investigator = ForeignKey(
        Researcher,
        on_delete=RESTRICT,
        verbose_name="Principal Investigator",
        help_text="The PI associated with the project.",
        related_name="project_piship",
    )

    members = ManyToManyField(
        Researcher,
        verbose_name="Project Members",
        related_name="project_membership",
        help_text="The researchers who are members of the project (and will have access to all associated datasets by default).",
    )

    is_valid = BooleanField(
        default=False, help_text="Entries require approval by site staff before they are visible."
    )

    def get_absolute_url(self) -> str:
        return f"/project/{self.pk}/"

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return str(self)


User = get_user_model()


@predicate
def is_project_member(user: User, project: Project) -> bool:
    """
    Does this user account correspond to a researcher who is a member of this project?

    :param user: User to check.
    :param project: The Project to check.
    :return: True if the user is a Researcher who is a member of this project, else False.
    """
    return (
        user
        and (user.researcher == project.principal_investigator)
        or (user.researcher in project.members.all())
    )


# Rules for database interactions with this source
# Conditions are tested on the user wanting to make the change
add_perm("app.add_project", is_active)
add_perm("app.change_project", is_project_member | is_staff)
add_perm("app.delete_project", is_staff)
add_perm("app.view_project", is_active)
