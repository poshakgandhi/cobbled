from typing import Any

from dash_bootstrap_templates import load_figure_template
from django.db.models import Count, QuerySet
from django.template import Template
from iommi import (
    Column,
    Header,
    Page,
    Table,
    html,
)
from pandas import DataFrame
from plotly.graph_objects import Figure, Histogram, Layout
from plotly.graph_objs.layout import XAxis, YAxis
from plotly.offline import plot


class IndexPage(Page):
    """
    Simple index page.
    """

    header = Header("Compact Object BBinary Live Experiments Database")
    p1 = html.p("Binaries are notoriously stubborn to pin down and extract robust solutions for, especially for compact object binaries. Very long period binaries will need monitoring over years to decades. Faint binaries require intensive monitoring to remove contaminants.")

    p2 = html.p("This platform has been cobbled together to tackle these issues *collaboratively*. Upload your RV measurements, combine them with data from others, and fit for orbital solutions.")

    p3 = html.p("The hope, and expectation, is that collaboratively the whole can be more than the individual parts.")

    p4 = html.p("Please use in the right spirit."
    )



class PrivacyPage(Page):
    """
    Simple privacy page.
    """

    header = Header("Privacy Notice")
    paragraph = html.p(
        # You can put text here, but the children come before it
        children=dict(
            first=html.p("You probably need a default privacy notice. They're easy to make: "),
            link=html.a(
                "ICO Template here",
                attrs__href="https://ico.org.uk/for-organisations/advice-for-small-organisations/privacy-notices-and-cookies/create-your-own-privacy-notice/privacy-notice-generator-for-customers-or-suppliers/",
            ),
            note=html.p(
                "Realistically, the best way to add this is to put it in a template file and include that."
            ),
        )
    )
