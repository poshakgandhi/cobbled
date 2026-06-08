from iommi import Header, Page, html


class ValidationViewPage(Page):
    """
    Simple index page.
    """

    header = Header("Validation Queue")
    p = html.p("Please select a validation queue to proceed.")
