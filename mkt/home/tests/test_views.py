import datetime

from nose.tools import eq_
from pyquery import PyQuery as pq

from amo.tests import app_factory, mock_es
from amo.urlresolvers import reverse

from mkt.browse.tests.test_views import BrowseBase
from mkt.webapps.models import Webapp


class TestHome(BrowseBase):

    def setUp(self):
        super(TestHome, self).setUp()
        self.url = reverse('home')

    @mock_es
    def test_page(self):
        r = self.client.get(self.url)
        eq_(r.status_code, 200)
        self.assertTemplateUsed(r, 'home/home.html')

    def test_featured_src(self):
        _, _, app = self.setup_featured()
        r = self.client.get(self.url)
        eq_(pq(r.content)('.mkt-tile').attr('href'),
            app.get_detail_url() + '?src=mkt-home')

    def test_tile_no_rating_link(self):
        r = self.client.get(self.url)
        assert not pq(r.content)('.mkt-tile .rating_link')

    @mock_es
    def test_featured_region_exclusions(self):
        self._test_featured_region_exclusions()

    def test_popular(self):
        self._test_popular()

    def test_popular_region_exclusions(self):
        self._test_popular_region_exclusions()

    def make_time_limited_feature(self):
        a = app_factory()
        fa = self.make_featured(app=a, category=None)
        fa.start_date = datetime.date(2012, 1, 1)
        fa.end_date = datetime.date(2012, 2, 1)
        fa.save()
        return a

    @mock_es
    def test_featured_time_excluded(self):
        a = self.make_time_limited_feature()
        for d in [datetime.date(2012, 1, 1),
                  datetime.date(2012, 1, 15),
                  datetime.date(2012, 2, 1)]:
            Webapp.now = staticmethod(lambda: d)
            eq_(self.get_pks('featured', self.url,  {'region': 'us'}), [a.id])

    @mock_es
    def test_featured_time_included(self):
        self.make_time_limited_feature()
        for d in [datetime.date(2011, 12, 15),
                  datetime.date(2012, 2, 2)]:
            Webapp.now = staticmethod(lambda: d)
            eq_(self.get_pks('featured', self.url, {'region': 'us'}), [])
