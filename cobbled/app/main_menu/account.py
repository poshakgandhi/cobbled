"""
Provides an interface to the AllAuth views.
They are:
 - accounts/
    - login
    - logout
    - inactive (handled automatically)
    - 3rdparty (handles the 3rd party account connection/disconnection)
"""

from iommi.main_menu import EXTERNAL, M

from app.forms.researcher import ProfileChangeForm, ProfileForm

account_submenu: M = M(
    display_name=lambda user, **_: user.get_full_name(),
    icon="user",
    include=lambda user, **_: user.is_authenticated and user.is_active,
    view=ProfileForm().as_view(),
    items=dict(
        change=M(
            icon="user-pen",
            view=ProfileChangeForm().as_view(),
        ),
        manage=M(
            icon="user-gear",
            url="/accounts/3rdparty/",
            view=EXTERNAL,
        ),
        logout=M(
            display_name="Sign Out",
            icon="right-from-bracket",
            url="/accounts/logout/",
            view=EXTERNAL,
        ),
    ),
)
