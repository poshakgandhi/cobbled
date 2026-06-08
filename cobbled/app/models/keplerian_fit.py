from django.db import models
from rules import add_perm, is_active, is_staff
from app.models.source import Source


class KeplerianFit(models.Model):
    """
    Model to store a saved Keplerian fit for a given source.
    """

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="fits")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Store MAP parameters, standard deviations, and credible intervals
    fit_parameters = models.JSONField(
        help_text="MAP values, standard deviations, and credible intervals"
    )

    # Store serialized samples for plotting the posterior orbit bundle
    sample_bundle = models.JSONField(
        help_text="Serialized JokerSamples subset for orbit bundle plotting"
    )

    # Hash of the radial velocity observations to identify data changes
    observation_hash = models.CharField(
        max_length=64,
        help_text="Deterministic SHA256 hash of the RV observations"
    )

    # Pre-rendered plot HTML to avoid expensive astropy/pytensor calculations on page load
    plot_html = models.TextField(
        null=True,
        blank=True,
        help_text="Pre-rendered Plotly HTML string of the orbit bundle and observations"
    )


    class Meta:
        get_latest_by = "created_at"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Fit for {self.source.name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


# Permission rules for KeplerianFit
add_perm("app.add_keplerianfit", is_active)
add_perm("app.change_keplerianfit", is_staff)
add_perm("app.delete_keplerianfit", is_staff)
add_perm("app.view_keplerianfit", is_active)
