from iommi import Form

from app.models import Project


class ProjectForm(Form):
    """
    Handles the common setup for project-based forms.
    """

    class Meta:
        auto__model = Project
