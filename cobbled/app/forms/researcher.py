from django.contrib.auth import get_user_model
from iommi import Form
from iommi.form import save_nested_forms

from app.models.researcher import Researcher

User = get_user_model()


class ResearcherForm(Form):
    """
    Handles the common setup for researcher-based forms.
    """

    class Meta:
        auto__model = Researcher


class ProfileForm(Form):
    """
    Handles displaying both user details and researcher details.
    """

    user = Form(
        auto=dict(
            model=User,
            include=["first_name", "last_name"],
        ),
        title=None,
        instance=lambda user, **_: user,
        editable=False,
    )
    researcher = Form(
        auto=dict(model=Researcher, exclude=["user"]),
        title=None,
        instance=lambda user, **_: user.researcher,
        editable=False,
    )

    class Meta:
        title = "Researcher Profile"


class ProfileChangeForm(Form):
    """
    Handles editing both user details and researcher details.
    """

    user = Form.edit(
        auto=dict(
            model=User,
            include=["first_name", "last_name"],
        ),
        title=None,
        instance=lambda user, **_: user,
    )
    researcher = Form.edit(
        auto=dict(model=Researcher, exclude=["user"]),
        title=None,
        instance=lambda user, **_: user.researcher,
    )

    class Meta:
        """
        Lets you nest edits to both the user and researcher model in one form.
        https://docs.iommi.rocks/cookbook_forms.html#how-do-i-nest-multiple-forms
        """

        actions__submit__post_handler = save_nested_forms
        title = "Change Profile"
