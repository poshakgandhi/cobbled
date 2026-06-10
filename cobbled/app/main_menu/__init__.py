"""
Main menu that describes the site views and URL structure,
as well as controlling access to the views.
"""

from iommi.admin import Admin
from iommi.main_menu import EXTERNAL, M, MainMenu

from app.main_menu.account import account_submenu
from app.main_menu.instrument import instrument_submenu
from app.main_menu.project import project_submenu
from app.main_menu.researcher import researcher_submenu
from app.main_menu.source import source_submenu
from app.main_menu.validation import validation_submenu
from app.pages import IndexPage, PrivacyPage
from app.pages.upload import UploadPage

main_menu = MainMenu(
    items=dict(
        index=M(
            render=False,
            path="",
            url="/",
            view=IndexPage().as_view(),
        ),
        source=source_submenu,
        upload=M(
            display_name="Upload Data",
            icon="upload",
            include=lambda user, **_: user.is_authenticated,
            url="/upload/",
            view=UploadPage().as_view(),
        ),
        instrument=instrument_submenu,
        researcher=researcher_submenu,
        # ---------------- This just adds a bar into the menu ----------------
        separator_1=M(view=EXTERNAL, template="app/main_menu/spacer.html"),
        project=project_submenu,
        # ---------------- This just adds a bar into the menu ----------------
        separator_2=M(
            include=lambda user, **_: user.is_authenticated,
            template="app/main_menu/spacer.html",
            view=EXTERNAL,
        ),
        account=account_submenu,
        sign_in=M(
            display_name="Sign In",
            icon="right-to-bracket",
            include=lambda user, **_: not user.is_authenticated,
            url="/accounts/login",
            view=EXTERNAL,
        ),
        sign_out=M(
            display_name="Sign Out",
            icon="right-from-bracket",
            include=lambda user, **_: user.is_authenticated,
            url="/accounts/logout/",
            view=EXTERNAL,
        ),
        validation_queue=validation_submenu,
        iommi_admin=M(
            display_name="Admin",
            icon="screwdriver-wrench",
            include=lambda user, **_: user.is_staff,
            paths=Admin.urls().urlpatterns,
            view=Admin.all_models(),
        ),
        # ---------------- This just adds a bar into the menu ----------------
        separator_3=M(view=EXTERNAL, template="app/main_menu/spacer.html"),
        help=M(
            icon="circle-info",
            url="https://Gaia-COB.github.io/gaia-cob-pmp/",
            view=EXTERNAL,
        ),
        privacy=M(
            icon="lock",
            url="/privacy/",
            view=PrivacyPage().as_view(),
        ),
    ),
)
