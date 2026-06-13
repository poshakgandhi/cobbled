from iommi import Header, Page, html
from app.models import Source, Instrument, Project, Researcher, Observation


class ValidationViewPage(Page):
    """
    Simple index page that shows links and counts of pending items in the validation queues.
    """

    header = Header("Validation Queue")
    p = html.p("Please select one of the validation queues below to review pending approvals:")

    grid = html.div(
        children=dict(
            source=html.a(
                children__text=lambda **_: f"Sources ({Source.objects.filter(is_valid=False).count()})",
                attrs__href="/validation_queue/source/",
                attrs__class={"btn btn-outline-primary m-2 p-3": True},
                attrs__style={"min-width": "200px", "text-align": "center", "font-weight": "bold", "text-decoration": "none"}
            ),
            instrument=html.a(
                children__text=lambda **_: f"Instruments ({Instrument.objects.filter(is_valid=False).count()})",
                attrs__href="/validation_queue/instrument/",
                attrs__class={"btn btn-outline-primary m-2 p-3": True},
                attrs__style={"min-width": "200px", "text-align": "center", "font-weight": "bold", "text-decoration": "none"}
            ),
            project=html.a(
                children__text=lambda **_: f"Projects ({Project.objects.filter(is_valid=False).count()})",
                attrs__href="/validation_queue/project/",
                attrs__class={"btn btn-outline-primary m-2 p-3": True},
                attrs__style={"min-width": "200px", "text-align": "center", "font-weight": "bold", "text-decoration": "none"}
            ),
            researcher=html.a(
                children__text=lambda **_: f"Researchers ({Researcher.objects.filter(user__is_active=False).count()})",
                attrs__href="/validation_queue/researcher/",
                attrs__class={"btn btn-outline-primary m-2 p-3": True},
                attrs__style={"min-width": "200px", "text-align": "center", "font-weight": "bold", "text-decoration": "none"}
            ),
            dataset=html.a(
                children__text=lambda **_: f"Datasets ({Observation.objects.filter(dataset__is_valid=False).count()})",
                attrs__href="/validation_queue/dataset/",
                attrs__class={"btn btn-outline-primary m-2 p-3": True},
                attrs__style={"min-width": "200px", "text-align": "center", "font-weight": "bold", "text-decoration": "none"}
            ),
        ),
        attrs__class={"d-flex flex-wrap justify-content-start mt-3": True}
    )
