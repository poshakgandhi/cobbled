from django.contrib.auth import get_user_model
from django.db.models import (
    CASCADE,
    RESTRICT,
    CharField,
    ForeignKey,
    Model,
    TextChoices,
    TextField,
)
from django.utils.translation import gettext_lazy as _
from rules import add_perm, is_active, is_staff, predicate

from app.models.instrument import Instrument
from app.models.project import Project


class Proposal(Model):
    """
    Model for an instrument proposal.
    """

    class Status(TextChoices):
        """
        The allowed entries for the Status field.
        """

        PLANNED = "p", _("Planned")
        SUBMITTED = "s", _("Submitted")
        ACCEPTED = "a", _("Accepted")
        REJECTED = "r", _("Rejected")

    status = CharField(
        max_length=1,
        choices=Status,
        default=Status.PLANNED,
        verbose_name="Proposal Status",
        help_text="The status of the proposal.",
    )

    description = TextField(
        null=False,
        blank=False,
        verbose_name="Proposal Description",
        help_text="A description of the proposal.",
    )

    instrument = ForeignKey(
        Instrument, on_delete=RESTRICT, help_text="The instrument used for the proposal."
    )

    project = ForeignKey(
        Project, on_delete=CASCADE, help_text="The project to which the proposal is affiliated."
    )

    def get_absolute_url(self) -> str:
        return f"/project/{self.project.pk}/proposal/{self.pk}/"

    def get_project_index(self) -> int:
        return self.project.proposal_set.filter(pk__lt=self.pk).count() + 1

    def __str__(self) -> str:
        return f"Proposal {self.get_project_index()}"

    def __repr__(self) -> str:
        return f"{self.project}: Proposal {self.get_project_index()}"


User = get_user_model()


@predicate
def is_linked_project_member(user: User, proposal: Proposal) -> bool:
    """
    Does this user account correspond to a researcher who is a member of the project linked to this proposal?

    :param user: User to check.
    :param proposal: The Proposal to check.
    :return: True if the user is a Researcher who is a member of this proposal's linked project, else False.
    """
    return (
        user
        and (user.researcher == proposal.project.principal_investigator)
        or (user.researcher in proposal.project.members.all())
    )


# Rules for database interactions with this source
# Conditions are tested on the user wanting to make the change
add_perm("app.add_proposal", is_active)
add_perm("app.change_proposal", is_linked_project_member | is_staff)
add_perm("app.delete_proposal", is_staff)
add_perm("app.view_proposal", is_active)
