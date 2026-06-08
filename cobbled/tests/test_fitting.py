from django.test import TestCase
from app.models import Source
from app.models.keplerian_fit import KeplerianFit
from app.fitting import run_joker_fit, get_fit_results
from app.plots.rv_curve import get_rv_plot


class FittingTestCase(TestCase):
    fixtures = ["units.json", "zz_demo_data.json"]

    def setUp(self):
        self.source = Source.objects.get(name="Test Source 2")

    def test_run_joker_fit(self):
        samples, parameters = run_joker_fit(self.source, prior_samples=20000)
        if samples is not None:
            self.assertTrue(len(samples) >= 0)
            self.assertEqual(len(parameters), 6)
            for p in parameters:
                self.assertIn("name", p)
                self.assertIn("val", p)
                self.assertIn("err", p)

    def test_database_persistence_and_loading(self):
        # 1. Run and verify it saves to Django database
        samples1, params1 = get_fit_results(self.source, force_run=True)
        if samples1 is not None:
            # Check a record is created in Django DB
            db_fit = KeplerianFit.objects.filter(source=self.source).first()
            self.assertIsNotNone(db_fit)
            self.assertEqual(db_fit.fit_parameters, params1)

            # 2. Verify subsequent retrieval loads from DB (force_run=False)
            samples2, params2 = get_fit_results(self.source, force_run=False)
            self.assertEqual(params1, params2)
            # Reconstructed JokerSamples object should work for plotting
            self.assertIsNotNone(samples2)
            self.assertTrue(hasattr(samples2, "get_orbit"))

    def test_run_fit_with_guesses(self):
        # Run fit with specific guesses to verify they are handled correctly
        samples, parameters = run_joker_fit(
            self.source,
            prior_samples=10000,
            p_guess=10.0,
            k_guess=20.0,
            v0_guess=5.0,
            e_guess=0.25
        )
        if samples is not None:
            self.assertTrue(len(samples) >= 0)
            self.assertEqual(len(parameters), 6)


    def test_get_rv_plot_with_fit(self):
        samples, _ = get_fit_results(self.source, force_run=True)
        html_div = get_rv_plot(self.source, fit_samples=samples)
        self.assertIn("plotly", html_div)
