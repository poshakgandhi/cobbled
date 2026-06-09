from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch
from app.models import Source, Instrument, Project, Observation, DataSet, Researcher
from app.pages.upload import parse_yaml_csv_data

User = get_user_model()


class UploadTestCase(TestCase):
    fixtures = [
        "units.json",
        "zz_demo_data_part1.json",
        "zz_demo_data_part2.json",
        "zz_demo_data_part3.json",
    ]

    def setUp(self):
        self.user_pi = User.objects.get(username="jc2a23soton@gmail.com")
        self.user_other = User.objects.get(username="testuser")
        
        # Ensure testuser has a Researcher profile for tests
        if not hasattr(self.user_other, "researcher"):
            Researcher.objects.create(user=self.user_other, affiliations="Test Affiliate")
            
        self.project = Project.objects.get(pk=2)  # Test Project (PI is jc2a23soton@gmail.com)
        self.instrument = Instrument.objects.get(pk=1)  # Test Instrument
        self.source = Source.objects.get(pk=1)  # Test Source

    def test_parse_yaml_csv_single_source(self):
        yaml_csv_data = """---
Source: Test Source 2
Instrument: HIRES
Project: Test Project
---
HJD, RV, RV_Error
2459791.9186, 131.9, 0.1
2459823.8525, 53.76, 0.2
"""
        initial_obs_count = Observation.objects.count()
        
        observations = parse_yaml_csv_data(
            text_content=yaml_csv_data,
            user=self.pi_user if hasattr(self, "pi_user") else self.user_pi
        )
        
        self.assertEqual(len(observations), 2)
        self.assertEqual(Observation.objects.count(), initial_obs_count + 2)
        
        # Verify fields on created observations
        for obs in observations:
            self.assertEqual(obs.source.name, "Test Source 2")
            self.assertEqual(obs.instrument.name, "HIRES")
            self.assertEqual(obs.project, self.project)
            self.assertEqual(obs.observer, self.user_pi.researcher)
            self.assertIsNotNone(obs.dataset)
            self.assertTrue(obs.is_valid)

    def test_parse_multi_source_csv(self):
        csv_data = """Source, HJD, RV, RV_Error, Instrument
Test Source, 2459791.9186, 131.9, 0.1, HIRES
Test Source 2, 2459823.8525, 53.76, 0.2, ESPRESSO
"""
        initial_obs_count = Observation.objects.count()
        
        observations = parse_yaml_csv_data(
            text_content=csv_data,
            user=self.user_pi
        )
        
        self.assertEqual(len(observations), 2)
        self.assertEqual(Observation.objects.count(), initial_obs_count + 2)
        
        obs1, obs2 = observations
        self.assertEqual(obs1.source.name, "Test Source")
        self.assertEqual(obs1.instrument.name, "HIRES")
        
        self.assertEqual(obs2.source.name, "Test Source 2")
        self.assertEqual(obs2.instrument.name, "ESPRESSO")

    def test_parse_errors_and_rollback(self):
        # This payload has a non-numeric RV on the second row
        malformed_data = """---
Source: Test Source 2
Instrument: HIRES
---
HJD, RV, RV_Error
2459791.9186, 131.9, 0.1
2459823.8525, bad_val, 0.2
"""
        initial_obs_count = Observation.objects.count()
        
        with self.assertRaises(ValueError) as ctx:
            parse_yaml_csv_data(
                text_content=malformed_data,
                user=self.user_pi
            )
            
        self.assertIn("Non-numeric value found", str(ctx.exception))
        
        # Verify transaction rolled back completely (0 observations created)
        self.assertEqual(Observation.objects.count(), initial_obs_count)

    def test_project_permission_check(self):
        # Make user_other not a staff/superuser to enforce permission checks
        self.user_other.is_staff = False
        self.user_other.is_superuser = False
        self.user_other.save()

        # testuser is not the PI or member of self.project
        yaml_csv_data = """---
Source: Test Source 2
Instrument: HIRES
Project: Test Project
---
HJD, RV, RV_Error
2459791.9186, 131.9, 0.1
"""
        with self.assertRaises(ValueError) as ctx:
            parse_yaml_csv_data(
                text_content=yaml_csv_data,
                user=self.user_other
            )
            
        self.assertIn("permission to add observations to project", str(ctx.exception))

    def test_missing_required_fields(self):
        # Missing Instrument in YAML and no default instrument passed
        bad_data = """---
Source: Test Source 2
---
HJD, RV, RV_Error
2459791.9186, 131.9, 0.1
"""
        with self.assertRaises(ValueError) as ctx:
            parse_yaml_csv_data(
                text_content=bad_data,
                user=self.user_pi
            )
        self.assertIn("Instrument not specified", str(ctx.exception))

    def test_upload_validation_and_visibility(self):
        from app.pages.source import source_has_rv_data

        # 1. Non-staff user uploads data for a NEW source
        yaml_csv_data = """---
Source: Brand New Source
Instrument: HIRES
Project: Test Project
---
HJD, RV, RV_Error
2459791.9186, 131.9, 0.1
2459823.8525, 53.76, 0.2
2459850.1234, -10.5, 0.3
"""
        # testuser is not staff
        self.user_other.is_staff = False
        self.user_other.save()

        # Grant access to project for testuser so they can upload
        self.project.members.add(self.user_other.researcher)

        observations = parse_yaml_csv_data(
            text_content=yaml_csv_data,
            user=self.user_other
        )

        new_source = Source.objects.get(name="Brand New Source")
        
        # Source must be unvalidated and owned by testuser's researcher
        self.assertFalse(new_source.is_valid)
        self.assertEqual(new_source.created_by, self.user_other.researcher)

        # Datasets must also be unvalidated
        for obs in observations:
            self.assertFalse(obs.dataset.is_valid)

        # source_has_rv_data should return True for the owner
        self.assertTrue(source_has_rv_data(new_source, user=self.user_other))

        # source_has_rv_data should return False for a different non-staff user
        other_user = User.objects.create_user(username="other_researcher", password="pwd")
        Researcher.objects.create(user=other_user, affiliations="Other Affil")
        self.assertFalse(source_has_rv_data(new_source, user=other_user))

        # source_has_rv_data should return True for staff user (since staff sees all)
        self.assertTrue(source_has_rv_data(new_source, user=self.user_pi))

    def test_auto_create_project_non_staff(self):
        # testuser is not staff
        self.user_other.is_staff = False
        self.user_other.is_superuser = False
        self.user_other.save()

        yaml_csv_data = """---
Source: New Source Temp
Instrument: HIRES
Project: Completely Brand New Project
---
HJD, RV, RV_Error
2459791.9186, 131.9, 0.1
"""
        observations = parse_yaml_csv_data(
            text_content=yaml_csv_data,
            user=self.user_other
        )
        
        self.assertEqual(len(observations), 1)
        project = Project.objects.get(name="Completely Brand New Project")
        # For non-staff, project must be unvalidated
        self.assertFalse(project.is_valid)
        # Principal investigator must be the uploader researcher
        self.assertEqual(project.principal_investigator, self.user_other.researcher)

    def test_auto_create_project_staff(self):
        self.user_pi.is_staff = True
        self.user_pi.is_superuser = True
        self.user_pi.save()

        yaml_csv_data = """---
Source: New Source Temp 2
Instrument: HIRES
Project: Staff Created Project
---
HJD, RV, RV_Error
2459791.9186, 131.9, 0.1
"""
        observations = parse_yaml_csv_data(
            text_content=yaml_csv_data,
            user=self.user_pi
        )
        
        self.assertEqual(len(observations), 1)
        project = Project.objects.get(name="Staff Created Project")
        # For staff, project must be validated directly
        self.assertTrue(project.is_valid)

    @patch('app.gaia_lookup.query_gaia_info_for_source')
    def test_parse_coordinates_and_gaia_lookup(self, mock_lookup):
        mock_lookup.return_value = (
            {
                "gaia_id": "9876543210123456",
                "parallax": 2.5,
                "parallax_error": 0.1,
                "pmra": 10.0,
                "pmra_error": 0.5,
                "pmdec": -20.0,
                "pmdec_error": 0.5,
                "phot_g_mean_mag": 12.0,
                "bp_rp": 0.8,
                "radial_velocity": 45.0,
                "radial_velocity_error": 1.2,
                "astrometric_excess_noise": 0.05,
                "astrometric_excess_noise_sig": 1.5,
            },
            123.45,
            -67.89,
            "Gaia Lookup Source"
        )
        
        yaml_csv_data = """---
Source: Gaia Lookup Source
Instrument: HIRES
RA: 123.45
Dec: -67.89
---
HJD, RV, RV_Error
2459791.9186, 131.9, 0.1
"""
        observations = parse_yaml_csv_data(
            text_content=yaml_csv_data,
            user=self.user_pi
        )
        
        self.assertEqual(len(observations), 1)
        source = Source.objects.get(name="Gaia Lookup Source")
        self.assertEqual(source.ra, 123.45)
        self.assertEqual(source.dec, -67.89)
        
        # Check that SourceGaiaInfo was created and populated
        self.assertTrue(hasattr(source, "gaiainfo"))
        gaiainfo = source.gaiainfo
        self.assertEqual(gaiainfo.gaia_id, "9876543210123456")
        self.assertEqual(gaiainfo.parallax, 2.5)
        self.assertEqual(gaiainfo.pmra, 10.0)
        self.assertEqual(gaiainfo.pmdec, -20.0)
        self.assertEqual(gaiainfo.phot_g_mean_mag, 12.0)
        self.assertEqual(gaiainfo.bp_rp, 0.8)
        self.assertEqual(gaiainfo.radial_velocity, 45.0)

    @patch('app.gaia_lookup.query_gaia_info_for_source')
    def test_gaia_lookup_failure_does_not_fail_ingestion(self, mock_lookup):
        mock_lookup.side_effect = Exception("API Timeout")
        
        yaml_csv_data = """---
Source: Resilient Source
Instrument: HIRES
---
HJD, RV, RV_Error
2459791.9186, 131.9, 0.1
"""
        observations = parse_yaml_csv_data(
            text_content=yaml_csv_data,
            user=self.user_pi
        )
        self.assertEqual(len(observations), 1)
        source = Source.objects.get(name="Resilient Source")
        self.assertFalse(hasattr(source, "gaiainfo"))

