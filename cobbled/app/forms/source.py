from iommi import Form

from app.models import Source, SourceGaiaInfo


class SourceForm(Form):
    """
    Handles the common setup for source-based forms.
    """

    class Meta:
        auto__model = Source
        fields = dict(
            name=dict(required=False),
            ra=dict(required=False, group="Coordinates", parse=lambda string_value, **_: float(string_value) if string_value else None),
                        dec=dict(required=False, group="Coordinates", parse=lambda string_value, **_: float(string_value) if string_value else None),
        )

        @staticmethod
        def post_validation(form, **_):
            name = form.fields.name.value
            ra = form.fields.ra.value
            dec = form.fields.dec.value

            if not name and (ra is None or dec is None):
                form.add_error("Either a source name or both coordinates (RA and Dec) must be entered.")
                return

            if name and (ra is None or dec is None):
                from app.gaia_lookup import query_gaia_info_for_source
                try:
                    info, res_ra, res_dec, res_name = query_gaia_info_for_source(name)
                    if res_ra is not None and res_dec is not None:
                        form.fields.ra.value = res_ra
                        form.fields.dec.value = res_dec
                    else:
                        form.add_error(f"Could not resolve coordinates for source name '{name}'. Please enter coordinates manually.")
                except Exception as e:
                    form.add_error(f"Error resolving coordinates for source name '{name}': {e}. Please enter coordinates manually.")

            elif (ra is not None and dec is not None) and not name:
                from app.gaia_lookup import query_gaia_info_for_source
                try:
                    info, res_ra, res_dec, res_name = query_gaia_info_for_source(None, ra, dec)
                    if res_name:
                        form.fields.name.value = res_name
                    else:
                        form.add_error(f"Could not resolve a name for coordinates ({ra}, {dec}). Please enter a name manually.")
                except Exception as e:
                    form.add_error(f"Error resolving name for coordinates ({ra}, {dec}): {e}. Please enter a name manually.")


class SourceGaiaInfoForm(Form):
    """
    Handles the common setup for source Gaia info-based forms.
    """

    class Meta:
        auto__model = SourceGaiaInfo
        fields = dict(
            parallax__group="Parallax",
            parallax_error__group="Parallax",
            pmra__group="PMRA",
            pmra_error__group="PMRA",
            pmdec__group="PMDEC",
            pmdec_error__group="PMDEC",
            radial_velocity__group="Radial Velocity",
            radial_velocity_error__group="Radial Velocity",
            astrometric_excess_noise__group="Astrometric Excess Noise",
            astrometric_excess_noise_sig__group="Astrometric Excess Noise",
        )
