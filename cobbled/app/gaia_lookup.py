import re
from astroquery.simbad import Simbad
from astroquery.gaia import Gaia
from astropy.coordinates import SkyCoord
from astropy.time import Time
import astropy.units as u


def query_gaia_info_for_source(source_name, ra=None, dec=None, radius_arcsec=1.0):
    """
    Queries Gaia and Simbad to resolve a source name/coordinates and retrieve its Gaia Info.
    """
    # 1. Try to extract Gaia ID from name (look for 15-20 digit integer) if name is provided
    match = re.search(r"\b\d{15,20}\b", source_name) if source_name else None
    gaia_row = None
    resolved_name = source_name

    if match:
        gaia_id = int(match.group(0))
        try:
            query = f"SELECT * FROM gaiadr3.gaia_source WHERE source_id = {gaia_id}"
            j = Gaia.launch_job(query)
            res = j.get_results()
            if len(res) > 0:
                gaia_row = res[0]
        except Exception:
            pass

    # 2. Try Simbad if RA/Dec are missing or 0.0, and name is provided
    pmra, pmdec = None, None
    if gaia_row is None and source_name and (
        ra is None or dec is None or (float(ra) == 0.0 and float(dec) == 0.0)
    ):
        try:
            # Configure Simbad to include proper motion fields
            try:
                Simbad.add_votable_fields("pmra", "pmdec")
            except Exception:
                pass
            res = Simbad.query_object(source_name)
            if res is not None and len(res) > 0:
                ra = float(res["ra"][0])
                dec = float(res["dec"][0])
                if "pmra" in res.colnames:
                    val = res["pmra"][0]
                    if val is not None and str(val) != "--" and str(val) != "":
                        pmra = float(val)
                if "pmdec" in res.colnames:
                    val = res["pmdec"][0]
                    if val is not None and str(val) != "--" and str(val) != "":
                        pmdec = float(val)
        except Exception:
            pass

    # 3. If name is not provided but coordinates are, resolve name via Simbad or Gaia
    if not resolved_name and ra is not None and dec is not None and not (float(ra) == 0.0 and float(dec) == 0.0):
        try:
            coord = SkyCoord(ra=float(ra), dec=float(dec), unit=(u.deg, u.deg))
            res = Simbad.query_region(coord, radius=10.0 * u.arcsec)
            if res is not None and len(res) > 0:
                resolved_name = str(res["main_id"][0])
                if resolved_name.startswith("NAME "):
                    resolved_name = resolved_name[5:]
        except Exception:
            pass

        if not resolved_name:
            try:
                query = f"""
                SELECT TOP 1 * FROM gaiadr3.gaia_source 
                WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, 10.0/3600.0)) = 1
                """
                j = Gaia.launch_job(query)
                res = j.get_results()
                if len(res) > 0:
                    resolved_name = str(res["designation"][0])
            except Exception:
                pass

    # 4. If we have coordinates, perform Gaia cone search
    if (
        gaia_row is None
        and ra is not None
        and dec is not None
        and not (float(ra) == 0.0 and float(dec) == 0.0)
    ):
        # Apply space motion propagation if proper motions are available
        search_ra = float(ra)
        search_dec = float(dec)
        if pmra is not None and pmdec is not None:
            try:
                c = SkyCoord(
                    ra=search_ra * u.deg,
                    dec=search_dec * u.deg,
                    pm_ra_cosdec=pmra * u.mas / u.yr,
                    pm_dec=pmdec * u.mas / u.yr,
                    obstime=Time("J2000"),
                )
                c_epoch = c.apply_space_motion(new_obstime=Time("J2016"))
                search_ra = float(c_epoch.ra.deg)
                search_dec = float(c_epoch.dec.deg)
            except Exception:
                pass

        # Perform Gaia TAP cone search (start with radius_arcsec)
        try:
            query = f"""
            SELECT * FROM gaiadr3.gaia_source 
            WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {search_ra}, {search_dec}, {radius_arcsec}/3600.0)) = 1
            """
            j = Gaia.launch_job(query)
            res = j.get_results()
            if len(res) > 0:
                # Find closest to search_ra, search_dec
                target_coord = SkyCoord(ra=search_ra * u.deg, dec=search_dec * u.deg)
                min_sep = None
                best_row = None
                for row in res:
                    row_coord = SkyCoord(ra=float(row["ra"]) * u.deg, dec=float(row["dec"]) * u.deg)
                    sep = target_coord.separation(row_coord).arcsec
                    if min_sep is None or sep < min_sep:
                        min_sep = sep
                        best_row = row
                gaia_row = best_row
        except Exception:
            pass

        # Fallback: if not found with 1.0 arcsec, try 10.0 arcsec
        if gaia_row is None:
            try:
                query = f"""
                SELECT * FROM gaiadr3.gaia_source 
                WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {search_ra}, {search_dec}, 10.0/3600.0)) = 1
                """
                j = Gaia.launch_job(query)
                res = j.get_results()
                if len(res) > 0:
                    target_coord = SkyCoord(ra=search_ra * u.deg, dec=search_dec * u.deg)
                    min_sep = None
                    best_row = None
                    for row in res:
                        row_coord = SkyCoord(
                            ra=float(row["ra"]) * u.deg, dec=float(row["dec"]) * u.deg
                        )
                        sep = target_coord.separation(row_coord).arcsec
                        if min_sep is None or sep < min_sep:
                            min_sep = sep
                            best_row = row
                    gaia_row = best_row
            except Exception:
                pass

    if gaia_row is None:
        return None, ra, dec, resolved_name

    # Build dictionary matching SourceGaiaInfo fields
    def clean_val(val, target_type=float):
        if val is None or str(val) == "--" or str(val) == "":
            return None
        # Handle astropy/numpy masked values
        try:
            if hasattr(val, "mask") and val.mask:
                return None
        except Exception:
            pass
        try:
            return target_type(val)
        except (ValueError, TypeError):
            return None

    info_data = {
        "gaia_id": clean_val(gaia_row["source_id"], str),
        "parallax": clean_val(gaia_row.get("parallax")),
        "parallax_error": clean_val(gaia_row.get("parallax_error")),
        "pmra": clean_val(gaia_row.get("pmra")),
        "pmra_error": clean_val(gaia_row.get("pmra_error")),
        "pmdec": clean_val(gaia_row.get("pmdec")),
        "pmdec_error": clean_val(gaia_row.get("pmdec_error")),
        "phot_g_mean_mag": clean_val(gaia_row.get("phot_g_mean_mag")),
        "bp_rp": clean_val(gaia_row.get("bp_rp")),
        "radial_velocity": clean_val(gaia_row.get("radial_velocity")),
        "radial_velocity_error": clean_val(gaia_row.get("radial_velocity_error")),
        "astrometric_excess_noise": clean_val(gaia_row.get("astrometric_excess_noise")),
        "astrometric_excess_noise_sig": clean_val(gaia_row.get("astrometric_excess_noise_sig")),
    }

    new_ra = clean_val(gaia_row.get("ra"))
    new_dec = clean_val(gaia_row.get("dec"))
    if not resolved_name:
        resolved_name = clean_val(gaia_row.get("designation"), str)

    return info_data, new_ra or ra, new_dec or dec, resolved_name


def query_and_save_gaia_info(source, user, ra=None, dec=None):
    """
    Invokes lookups and saves the retrieved Gaia Info to the database.
    Does not crash on failures.
    """
    # If SourceGaiaInfo already exists, do not query
    if hasattr(source, "gaiainfo"):
        return

    # Check/resolve ra and dec
    source_ra = float(source.ra) if source.ra else 0.0
    source_dec = float(source.dec) if source.dec else 0.0

    if ra is None or dec is None or (float(ra) == 0.0 and float(dec) == 0.0):
        ra = source_ra
        dec = source_dec

    try:
        info_data, updated_ra, updated_dec, resolved_name = query_gaia_info_for_source(source.name, ra, dec)

        # Update source coordinates if they were previously 0.0
        if updated_ra is not None and updated_dec is not None:
            if source_ra == 0.0 and source_dec == 0.0:
                source.ra = updated_ra
                source.dec = updated_dec
                source.save()

        if info_data:
            from app.models import SourceGaiaInfo

            SourceGaiaInfo.objects.create(
                source=source,
                is_valid=source.is_valid,  # match source validation
                **info_data,
            )
    except Exception as e:
        print(f"Warning: Failed to fetch Gaia Info for source '{source.name}': {e}")
