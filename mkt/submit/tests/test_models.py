from nose.tools import eq_

import amo
import amo.tests
from mkt.submit.models import AppSubmissionChecklist
from mkt.webapps.models import Webapp


class TestAppSubmissionChecklist(amo.tests.TestCase):
    fixtures = ['webapps/337141-steamcube']

    def setUp(self):
        self.webapp = Webapp.objects.get(id=337141)
        self.cl = AppSubmissionChecklist.objects.create(addon=self.webapp)

    def test_default(self):
        eq_(self.cl.get_completed(), [])

    def test_terms(self):
        self.cl.update(terms=True)
        eq_(self.cl.get_completed(), ['terms'])

    def test_manifest(self):
        self.cl.update(terms=True, manifest=True)
        eq_(self.cl.get_completed(), ['terms', 'manifest'])

    def test_details(self):
        self.cl.update(terms=True, manifest=True, details=True)
        eq_(self.cl.get_completed(), ['terms', 'manifest', 'details'])

    def test_payments(self):
        self.cl.update(terms=True, manifest=True, details=True, payments=True)
        eq_(self.cl.get_completed(),
            ['terms', 'manifest', 'details', 'payments'])

    def test_skipped_details(self):
        self.cl.update(terms=True, manifest=True, payments=True)
        eq_(self.cl.get_completed(), ['terms', 'manifest', 'payments'])

    def test_next_details(self):
        self.cl.update(terms=True, manifest=True)
        eq_(self.cl.get_next(), 'details')

    def test_next_skipped_details(self):
        self.cl.update(terms=True, manifest=True, payments=True)
        eq_(self.cl.get_next(), 'details')

    def test_next_skipped_payments(self):
        self.cl.update(terms=True, manifest=True, details=True)
        eq_(self.cl.get_next(), 'payments')

    def test_next_payments(self):
        self.cl.update(terms=True, manifest=True, details=True, payments=True)
        eq_(self.cl.get_next(), None)
