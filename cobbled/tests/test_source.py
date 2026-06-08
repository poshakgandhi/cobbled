from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from unittest.mock import patch
from app.models import Source, SourceGaiaInfo, Researcher
from app.forms.source import SourceForm
from app.pages.source import add_gaiainfo_view

User = get_user_model()

class SourceTestCase(TestCase):
    fixtures = ["units.json", "zz_demo_data.json"]

    def setUp(self):
        self.user = User.objects.get(username="jc2a23soton@gmail.com")
        if not hasattr(self.user, "researcher"):
            Researcher.objects.create(user=self.user, affiliations="Test Affiliate")
        self.source = Source.objects.create(
            name="GJ 1214",
            ra=0.0,
            dec=0.0,
            is_valid=True,
            created_by=self.user.researcher
        )

    @patch('app.gaia_lookup.query_gaia_info_for_source')
    def test_source_form_resolve_coordinates(self, mock_lookup):
        mock_lookup.return_value = (
            None,
            258.8289,
            4.9639,
            "GJ 1214"
        )
        req = RequestFactory().post('/', data={
            'name': 'GJ 1214',
            '-submit': ''
        })
        form = SourceForm.create().bind(request=req)
        self.assertTrue(form.is_valid(), form.get_errors())
        
        source = Source()
        form.apply(source)
        self.assertEqual(source.name, "GJ 1214")
        self.assertEqual(source.ra, 258.8289)
        self.assertEqual(source.dec, 4.9639)

    @patch('app.gaia_lookup.query_gaia_info_for_source')
    def test_source_form_resolve_name(self, mock_lookup):
        mock_lookup.return_value = (
            None,
            258.8289,
            4.9639,
            "GJ 1214"
        )
        req = RequestFactory().post('/', data={
            'ra': '258.8289',
            'dec': '4.9639',
            '-submit': ''
        })
        form = SourceForm.create().bind(request=req)
        self.assertTrue(form.is_valid(), form.get_errors())
        
        source = Source()
        form.apply(source)
        self.assertEqual(source.name, "GJ 1214")
        self.assertEqual(source.ra, 258.8289)
        self.assertEqual(source.dec, 4.9639)

    def test_source_form_missing_all(self):
        req = RequestFactory().post('/', data={
            '-submit': ''
        })
        form = SourceForm.create().bind(request=req)
        self.assertFalse(form.is_valid())
        self.assertIn("Either a source name or both coordinates", str(form.get_errors()))

    @patch('django.contrib.messages.success')
    @patch('django.contrib.messages.error')
    @patch('app.gaia_lookup.query_gaia_info_for_source')
    def test_add_gaia_info_view(self, mock_lookup, mock_msg_error, mock_msg_success):
        mock_lookup.return_value = (
            {
                "gaia_id": "123456789",
                "parallax": 2.0,
            },
            258.8289,
            4.9639,
            "GJ 1214"
        )

        # GET request to add_gaiainfo_view
        req_get = RequestFactory().get('/')
        req_get.user = self.user
        page = add_gaiainfo_view(req_get, self.source)
        self.assertIsNotNone(page)

        # POST request to save Gaia Info
        req_post = RequestFactory().post('/')
        req_post.user = self.user
        response = add_gaiainfo_view(req_post, self.source)
        
        self.assertEqual(response.status_code, 302)
        
        self.source.refresh_from_db()
        self.assertEqual(self.source.ra, 258.8289)
        self.assertEqual(self.source.dec, 4.9639)
        self.assertTrue(hasattr(self.source, "gaiainfo"))
        self.assertEqual(self.source.gaiainfo.gaia_id, "123456789")
        self.assertEqual(self.source.gaiainfo.parallax, 2.0)
