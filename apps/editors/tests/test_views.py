# -*- coding: utf8 -*-
from datetime import datetime, timedelta
import json
import re
import time

from django.conf import settings
from django.core import mail

from mock import patch, patch_object
from nose.tools import eq_
from pyquery import PyQuery as pq
import test_utils
from waffle.models import Switch

import amo
from amo.urlresolvers import reverse
from amo.tests import formset, initial
from addons.models import Addon, AddonUser
from applications.models import Application
from cake.urlresolvers import remora_url
from devhub.models import ActivityLog
from editors.models import EditorSubscription, EventLog
from files.models import Approval, Platform, File
import reviews
from reviews.models import Review, ReviewFlag
from users.models import UserProfile
from versions.models import Version, AppVersion, ApplicationsVersions
from zadmin.models import set_config
from . test_models import create_addon_file


class EditorTest(test_utils.TestCase):
    fixtures = ('base/users', 'editors/pending-queue', 'base/approvals')

    def login_as_admin(self):
        assert self.client.login(username='admin@mozilla.com',
                                 password='password')

    def login_as_editor(self):
        assert self.client.login(username='editor@mozilla.com',
                                 password='password')

    def make_review(self, username='a'):
        u = UserProfile.objects.create(username=username)
        a = Addon.objects.create(name='yermom', type=amo.ADDON_EXTENSION)
        return Review.objects.create(user=u, addon=a)


class TestEventLog(EditorTest):
    def setUp(self):
        self.login_as_editor()
        amo.set_user(UserProfile.objects.get(username='editor'))
        review = self.make_review()
        for i in xrange(4):
            amo.log(amo.LOG.APPROVE_REVIEW, review, review.addon)
            amo.log(amo.LOG.DELETE_REVIEW, review.id, review.addon)

    def test_log(self):
        r = self.client.get(reverse('editors.eventlog'))
        eq_(r.status_code, 200)

    def test_start_filter(self):
        r = self.client.get(reverse('editors.eventlog') + '?start=3011-01-01')
        eq_(r.status_code, 200)

    def test_enddate_filter(self):
        """
        Make sure that if our end date is 1/1/2011, that we include items from
        1/1/2011.  To not do as such would be dishonorable.
        """
        review = self.make_review(username='b')
        amo.log(amo.LOG.APPROVE_REVIEW, review, review.addon,
                created=datetime(2011, 1, 1))

        r = self.client.get(reverse('editors.eventlog') + '?end=2011-01-01')
        eq_(r.status_code, 200)
        doc = pq(r.content)
        eq_(doc('tbody td').eq(0).text(), 'Jan 1, 2011 12:00:00 AM')

    def test_action_filter(self):
        """
        Based on setup we should only see 30 items if we filter for deleted
        reviews.
        """
        r = self.client.get(reverse('editors.eventlog') + '?filter=deleted')
        doc = pq(r.content)
        eq_(len(doc('tbody tr')), 4)

    def test_no_results(self):
        r = self.client.get(reverse('editors.eventlog') + '?end=' +
                            '2004-01-01')

        assert 'No events found for this period.' in r.content

    def test_breadcrumbs(self):
        r = self.client.get(reverse('editors.eventlog'))
        doc = pq(r.content)
        list_items = doc('ol.breadcrumbs li')
        eq_(list_items.length, 2)

        eq_(list_items.eq(0).find('a').text(), "Editor Tools")
        eq_(list_items.eq(1).text(), "Moderated Review Log")


class TestEventLogDetail(TestEventLog):
    def test_me(self):
        id = ActivityLog.objects.editor_events()[0].id
        r = self.client.get(reverse('editors.eventlog.detail', args=[id]))
        eq_(r.status_code, 200)


class TestReviewLog(EditorTest):
    def setUp(self):
        self.login_as_editor()

    def make_approvals(self, count=6):
        Platform.objects.create(id=amo.PLATFORM_ALL.id)
        u = UserProfile.objects.filter()[0]
        for i in xrange(count):
            a = Addon.objects.create(type=amo.ADDON_EXTENSION)
            v = Version.objects.create(addon=a)
            amo.log(amo.LOG.REJECT_VERSION, a, v, user=u,
                    details={'comments': 'youwin'})

    def make_an_approval(self, action):
        u = UserProfile.objects.filter()[0]
        a = Addon.objects.create(type=amo.ADDON_EXTENSION)
        v = Version.objects.create(addon=a)
        amo.log(action, a, v, user=u, details={'comments': 'youwin'})

    def test_basic(self):
        self.make_approvals()
        r = self.client.get(reverse('editors.reviewlog'))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        assert doc('.listing button'), 'No filters.'
        # Should have 6 showing.
        eq_(len(doc('tbody tr').not_('.hide')), 6)
        eq_(doc('tbody tr.hide').eq(0).text(), 'youwin')

    def test_xss(self):
        u = UserProfile.objects.filter()[0]
        a = Addon.objects.create(type=amo.ADDON_EXTENSION,
                                 name="<script>alert('')</script>")
        v = Version.objects.create(addon=a)
        amo.log(amo.LOG.REJECT_VERSION, a, v, user=u,
                details={'comments': 'xss!'})

        self.make_approvals(count=0)
        r = self.client.get(reverse('editors.reviewlog'))
        eq_(r.status_code, 200)
        doc = pq(r.content)

        inner_html = doc('tbody tr td').eq(1).html()

        assert "&lt;script&gt;" in inner_html
        assert "<script>" not in inner_html

    def test_end_filter(self):
        """
        Let's use today as an end-day filter and make sure we see stuff if we
        filter.
        """
        self.make_approvals()
        # Make sure we show the stuff we just made.
        date = time.strftime('%Y-%m-%d')
        r = self.client.get(reverse('editors.reviewlog') + '?end=' + date)
        eq_(r.status_code, 200)
        doc = pq(r.content)
        eq_(len(doc('tbody tr').not_('.hide')), 6)
        eq_(doc('tbody tr.hide').eq(0).text(), 'youwin')

    def test_end_filter_wrong(self):
        """
        Let's use today as an end-day filter and make sure we see stuff if we
        filter.
        """
        self.make_approvals()
        date = 'wrong!'
        r = self.client.get(reverse('editors.reviewlog') + '?end=' + date)
        # If this is broken, we'll get a traceback.
        eq_(r.status_code, 200)

        doc = pq(r.content)
        eq_(doc('#log-listing tr:not(.hide)').length, 7)

    def test_breadcrumbs(self):
        r = self.client.get(reverse('editors.reviewlog'))
        doc = pq(r.content)
        list_items = doc('ol.breadcrumbs li')
        eq_(list_items.length, 2)

        eq_(list_items.eq(0).find('a').text(), "Editor Tools")
        eq_(list_items.eq(1).text(), "Add-on Review Log")

    @patch('devhub.models.ActivityLog.arguments')
    def test_addon_missing(self, arguments):
        self.make_approvals()
        arguments.return_value = []
        r = self.client.get(reverse('editors.reviewlog'))
        doc = pq(r.content)
        eq_(doc('#log-listing tr td')[1].text.strip(),
            'Add-on has been deleted.')

    def test_request_info_logs(self):
        self.make_an_approval(amo.LOG.REQUEST_INFORMATION)
        r = self.client.get(reverse('editors.reviewlog'))
        doc = pq(r.content)
        eq_(doc('#log-listing tr td a')[1].text.strip(),
            'needs more information')

    def test_super_review_logs(self):
        self.make_an_approval(amo.LOG.REQUEST_SUPER_REVIEW)
        r = self.client.get(reverse('editors.reviewlog'))
        doc = pq(r.content)
        eq_(doc('#log-listing tr td a')[1].text.strip(),
            'needs super review')


class TestHome(EditorTest):
    """Test the page at /editors."""
    def setUp(self):
        self.login_as_editor()
        self.user = UserProfile.objects.get(id=5497308)
        self.user.display_name = 'editor'
        self.user.save()
        amo.set_user(self.user)

    def approve_reviews(self):
        Platform.objects.create(id=amo.PLATFORM_ALL.id)
        u = self.user

        now = datetime.now()
        created = datetime(now.year - 1, now.month, 1)

        for i in xrange(4):
            a = Addon.objects.create(type=amo.ADDON_EXTENSION)
            v = Version.objects.create(addon=a)

            amo.set_user(u)
            amo.log(amo.LOG['APPROVE_VERSION'], a, v)

    def test_approved_review(self):
        review = self.make_review()
        amo.log(amo.LOG.APPROVE_REVIEW, review, review.addon)
        r = self.client.get(reverse('editors.home'))
        doc = pq(r.content)
        eq_(doc('.row').eq(0).text().strip().split('.')[0],
            'editor approved Review for yermom ')

    def test_deleted_review(self):
        review = self.make_review()
        amo.log(amo.LOG.DELETE_REVIEW, review.id, review.addon)
        r = self.client.get(reverse('editors.home'))
        doc = pq(r.content)
        eq_(doc('.row').eq(0).text().strip().split('.')[0],
            'editor deleted review %d' % review.id)

    def test_stats_total(self):
        self.approve_reviews()

        r = self.client.get(reverse('editors.home'))
        doc = pq(r.content)

        div = doc('#editors-stats .editor-stats-table:eq(1)')

        display_name = div.find('td')[0].text
        eq_(display_name, self.user.display_name)

        approval_count = div.find('td')[1].text
        eq_(int(approval_count), 4)

    def test_stats_monthly(self):
        self.approve_reviews()

        r = self.client.get(reverse('editors.home'))
        doc = pq(r.content)

        div = doc('#editors-stats .editor-stats-table:eq(1)')

        display_name = div.find('td')[0].text
        eq_(display_name, self.user.display_name)

        approval_count = div.find('td')[1].text
        eq_(int(approval_count), 4)

    def test_new_editors(self):
        EventLog(type='admin', action='group_addmember', changed_id=2,
                 added=self.user.id, user=self.user).save()

        r = self.client.get(reverse('editors.home'))
        doc = pq(r.content)

        div = doc('#editors-stats .editor-stats-table:eq(2)')

        name = div.find('td a')[0].text.strip()
        eq_(name, self.user.display_name)


class QueueTest(EditorTest):
    fixtures = ['base/users']

    def setUp(self):
        super(QueueTest, self).setUp()
        self.login_as_editor()
        self.versions = {}
        self.addon_file(u'Pending One', u'0.1',
                        amo.STATUS_PUBLIC, amo.STATUS_UNREVIEWED)
        self.addon_file(u'Pending Two', u'0.1',
                        amo.STATUS_PUBLIC, amo.STATUS_UNREVIEWED)
        self.addon_file(u'Nominated One', u'0.1',
                        amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED)
        self.addon_file(u'Nominated Two', u'0.1',
                        amo.STATUS_LITE_AND_NOMINATED, amo.STATUS_UNREVIEWED)
        self.addon_file(u'Prelim One', u'0.1',
                        amo.STATUS_LITE, amo.STATUS_UNREVIEWED)
        self.addon_file(u'Prelim Two', u'0.1',
                        amo.STATUS_UNREVIEWED, amo.STATUS_UNREVIEWED)
        self.addon_file(u'Public', u'0.1',
                        amo.STATUS_PUBLIC, amo.STATUS_LISTED)

    def addon_file(self, *args, **kw):
        a = create_addon_file(*args, **kw)
        self.versions[unicode(a['addon'].name)] = a['version']


class TestQueueBasics(QueueTest):

    def test_only_viewable_by_editor(self):
        self.client.logout()
        assert self.client.login(username='regular@mozilla.com',
                                 password='password')
        r = self.client.get(reverse('editors.queue_pending'))
        eq_(r.status_code, 403)

    def test_invalid_page(self):
        r = self.client.get(reverse('editors.queue_pending'),
                            data={'page': 999})
        eq_(r.status_code, 200)
        eq_(r.context['page'].number, 1)

    def test_invalid_per_page(self):
        r = self.client.get(reverse('editors.queue_pending'),
                            data={'per_page': '<garbage>'})
        # No exceptions:
        eq_(r.status_code, 200)

    def test_redirect_to_review(self):
        r = self.client.get(reverse('editors.queue_pending'), data={'num': 2})
        self.assertRedirects(r,
                    reverse('editors.review',
                            args=[self.versions['Pending Two'].id]) + '?num=2')

    def test_invalid_review_ignored(self):
        r = self.client.get(reverse('editors.queue_pending'), data={'num': 9})
        eq_(r.status_code, 200)

    def test_garbage_review_num_ignored(self):
        r = self.client.get(reverse('editors.queue_pending'),
                            data={'num': 'not-a-number'})
        eq_(r.status_code, 200)

    def test_grid_headers(self):
        r = self.client.get(reverse('editors.queue_pending'))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        eq_(doc('table.data-grid tr th:eq(0)').text(), u'Addon')
        eq_(doc('table.data-grid tr th:eq(1)').text(), u'Type')
        eq_(doc('table.data-grid tr th:eq(2)').text(), u'Waiting Time')
        eq_(doc('table.data-grid tr th:eq(3)').text(), u'Flags')
        eq_(doc('table.data-grid tr th:eq(4)').text(), u'Applications')
        eq_(doc('table.data-grid tr th:eq(5)').text(),
            u'Additional Information')

    def test_no_results(self):
        File.objects.all().delete()
        r = self.client.get(reverse('editors.queue_pending'))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        eq_(doc('.queue-outer .no-results').length, 1)

    def test_no_paginator_when_on_single_page(self):
        r = self.client.get(reverse('editors.queue_pending'))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        eq_(doc('.pagination').length, 0)

    def test_paginator_when_many_pages(self):
        q = File.objects.exclude(version__in=(self.versions['Nominated One'],
                                              self.versions['Nominated Two']))
        q.delete()
        r = self.client.get(reverse('editors.queue_nominated'),
                            data={'per_page': 1})
        eq_(r.status_code, 200)
        doc = pq(r.content)
        eq_(doc('.data-grid-top .num-results').text(),
            u'Results 1 \u2013 1 of 2')
        eq_(doc('.data-grid-bottom .num-results').text(),
            u'Results 1 \u2013 1 of 2')

    def test_navbar_queue_counts(self):
        r = self.client.get(reverse('editors.home'))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        eq_(doc('#navbar li.top ul').eq(0).text(),
            'Full Reviews (2) Pending Updates (2) '
            'Preliminary Reviews (2) Moderated Reviews (0)')

    def test_legacy_queue_sort(self):
        sorts = (
            ['age', 'Waiting Time'],
            ['name', 'Addon'],
            ['type', 'Type'],
        )
        for key, text in sorts:
            url = reverse('editors.queue_pending') + '?sort=%s' % key
            response = self.client.get(url)
            eq_(response.status_code, 200)
            doc = pq(response.content)
            eq_(doc('th.ordered a').text(), text)

    def test_full_reviews_bar(self):
        addon = Addon.objects.filter(status=amo.STATUS_LITE_AND_NOMINATED)[0]

        review_data = ((1, (0, 0, 100), 2),
                       (8, (0, 50, 50), 1),
                       (11, (50, 0, 50), 1))

        style = lambda w: "width:%s%%" % (float(w) if w > 0 else 0)

        for (days, widths, under_7) in review_data:
            new_nomination = datetime.now() - timedelta(days=days)
            addon.versions.all()[0].update(nomination=new_nomination)

            r = self.client.get(reverse('editors.home'))
            doc = pq(r.content)

            div = doc('#editors-stats-charts .editor-stats-table:eq(0)')

            eq_(doc('.waiting_old', div).attr('style'), style(widths[0]))
            eq_(doc('.waiting_med', div).attr('style'), style(widths[1]))
            eq_(doc('.waiting_new', div).attr('style'), style(widths[2]))

            assert "%s submi" % under_7 in doc('div>div:eq(0)', div).text()

    def test_pending_bar(self):
        review_data = ((1, (0, 0, 100), 2),
                       (8, (0, 50, 50), 1),
                       (11, (50, 0, 50), 1))

        style = lambda w: "width:%s%%" % (float(w) if w > 0 else 0)

        for (days, widths, under_7) in review_data:
            addon = self.versions['Pending One'].addon
            new_created = datetime.now() - timedelta(days=days)
            version = addon.versions.all()[0]
            version.modified = new_created
            version.created = new_created
            version.save()

            # We have to re-set the status of the add-on after saving version
            addon.update(status=amo.STATUS_PUBLIC)

            r = self.client.get(reverse('editors.home'))
            doc = pq(r.content)

            div = doc('#editors-stats-charts .editor-stats-table:eq(1)')

            eq_(doc('.waiting_old', div).attr('style'), style(widths[0]))
            eq_(doc('.waiting_med', div).attr('style'), style(widths[1]))
            eq_(doc('.waiting_new', div).attr('style'), style(widths[2]))

            assert "%s submi" % under_7 in doc('div>div:eq(0)', div).text()

    def test_prelim_bar(self):
        review_data = ((1, (0, 0, 100), 2),
                       (8, (0, 50, 50), 1),
                       (11, (50, 0, 50), 1))

        style = lambda w: "width:%s%%" % (float(w) if w > 0 else 0)

        for (days, widths, under_7) in review_data:
            addon = self.versions['Prelim One'].addon
            new_created = datetime.now() - timedelta(days=days)
            version = addon.versions.all()[0]
            version.modified = new_created
            version.created = new_created
            version.save()

            r = self.client.get(reverse('editors.home'))
            doc = pq(r.content)

            div = doc('#editors-stats-charts .editor-stats-table:eq(2)')

            eq_(doc('.waiting_old', div).attr('style'), style(widths[0]))
            eq_(doc('.waiting_med', div).attr('style'), style(widths[1]))
            eq_(doc('.waiting_new', div).attr('style'), style(widths[2]))

            assert "%s submi" % under_7 in doc('div>div:eq(0)', div).text()


class TestPendingQueue(QueueTest):

    def test_results(self):
        r = self.client.get(reverse('editors.queue_pending'))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        row = doc('table.data-grid tr:eq(1)')
        eq_(doc('td:eq(0)', row).text(), u'Pending One 0.1')
        eq_(doc('td a:eq(0)', row).attr('href'),
            reverse('editors.review',
                    args=[self.versions[u'Pending One'].id]) + '?num=1')
        row = doc('table.data-grid tr:eq(2)')
        eq_(doc('td:eq(0)', row).text(), u'Pending Two 0.1')
        eq_(doc('a:eq(0)', row).attr('href'),
            reverse('editors.review',
                    args=[self.versions[u'Pending Two'].id]) + '?num=2')

    def test_queue_count(self):
        r = self.client.get(reverse('editors.queue_pending'))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        eq_(doc('.tabnav li a:eq(1)').text(), u'Pending Updates (2)')
        eq_(doc('.tabnav li a:eq(1)').attr('href'),
            reverse('editors.queue_pending'))

    def test_breadcrumbs(self):
        r = self.client.get(reverse('editors.queue_pending'))
        doc = pq(r.content)
        list_items = doc('ol.breadcrumbs li')
        eq_(list_items.length, 2)

        eq_(list_items.eq(0).find('a').text(), "Editor Tools")
        eq_(list_items.eq(1).text(), "Pending Updates")


class TestNominatedQueue(QueueTest):

    def test_results(self):
        r = self.client.get(reverse('editors.queue_nominated'))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        row = doc('table.data-grid tr:eq(1)')
        eq_(doc('td:eq(0)', row).text(), u'Nominated One 0.1')
        eq_(doc('td a:eq(0)', row).attr('href'),
            reverse('editors.review',
                    args=[self.versions[u'Nominated One'].id]) + '?num=1')
        row = doc('table.data-grid tr:eq(2)')
        eq_(doc('td:eq(0)', row).text(), u'Nominated Two 0.1')
        eq_(doc('a:eq(0)', row).attr('href'),
            reverse('editors.review',
                    args=[self.versions[u'Nominated Two'].id]) + '?num=2')

    def test_results_two_versions(self):
        ver = self.versions['Nominated Two'].addon.versions.all()[0]
        file = ver.files.all()[0]

        original_nomination = ver.nomination
        ver.nomination = ver.nomination - timedelta(days=1)
        ver.save()

        ver.pk = None
        ver.nomination = original_nomination
        ver.version = "0.2"
        ver.save()

        file.pk = None
        file.version = ver
        file.save()

        r = self.client.get(reverse('editors.queue_nominated'))
        eq_(r.status_code, 200)
        doc = pq(r.content)

        row = doc('table.data-grid tr:eq(2)')
        eq_(doc('td:eq(0)', row).text(), u'Nominated Two 0.2')

        # Make sure the time isn't the same as the original time.
        # (We're using the other row as a constant for comparison.)
        row_constant = doc('table.data-grid tr:eq(1)')
        eq_(doc('td:eq(2)', row).text(), doc('td:eq(2)', row_constant).text())

    def test_queue_count(self):
        r = self.client.get(reverse('editors.queue_nominated'))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        eq_(doc('.tabnav li a:eq(0)').text(), u'Full Reviews (2)')
        eq_(doc('.tabnav li a:eq(0)').attr('href'),
            reverse('editors.queue_nominated'))


class TestPreliminaryQueue(QueueTest):

    def test_results(self):
        r = self.client.get(reverse('editors.queue_prelim'))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        row = doc('table.data-grid tr:eq(1)')
        eq_(doc('td:eq(0)', row).text(), u'Prelim One 0.1')
        eq_(doc('td a:eq(0)', row).attr('href'),
            reverse('editors.review',
                    args=[self.versions[u'Prelim One'].id]) + '?num=1')
        row = doc('table.data-grid tr:eq(2)')
        eq_(doc('td:eq(0)', row).text(), u'Prelim Two 0.1')
        eq_(doc('a:eq(0)', row).attr('href'),
            reverse('editors.review',
                    args=[self.versions[u'Prelim Two'].id]) + '?num=2')

    def test_queue_count(self):
        r = self.client.get(reverse('editors.queue_prelim'))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        eq_(doc('.tabnav li a:eq(2)').text(), u'Preliminary Reviews (2)')
        eq_(doc('.tabnav li a:eq(2)').attr('href'),
            reverse('editors.queue_prelim'))

    def test_breadcrumbs(self):
        r = self.client.get(reverse('editors.queue_prelim'))
        doc = pq(r.content)
        list_items = doc('ol.breadcrumbs li')
        eq_(list_items.length, 2)

        eq_(list_items.eq(0).find('a').text(), "Editor Tools")
        eq_(list_items.eq(1).text(), "Preliminary Reviews")


class TestModeratedQueue(QueueTest):
    fixtures = ['base/users', 'base/apps', 'reviews/dev-reply.json']

    def setUp(self):
        self.url = reverse('editors.queue_moderated')
        url_flag = reverse('reviews.flag', args=['a1865', 218468])

        self.login_as_editor()
        response = self.client.post(url_flag, {'flag': ReviewFlag.SPAM})
        eq_(response.status_code, 200)

        eq_(ReviewFlag.objects.filter(flag=ReviewFlag.SPAM).count(), 1)
        eq_(Review.objects.filter(editorreview=True).count(), 1)

    def test_results(self):
        r = self.client.get(reverse('editors.queue_moderated'))
        eq_(r.status_code, 200)
        doc = pq(r.content)

        rows = doc('#reviews-flagged .review-flagged:not(.review-saved)')
        eq_(len(rows), 1)

        row = rows[0]

        assert re.findall("Don't use Firefox", doc('h3', row).text())

        # Default is "Skip"
        assert doc('#id_form-0-action_1:checked')

    def setup_actions(self, action):
        ctx = self.client.get(self.url).context
        fs = initial(ctx['reviews_formset'].forms[0])

        eq_(len(Review.objects.filter(addon=1865)), 2)

        data_formset = formset(fs)
        data_formset['form-0-action'] = action

        r = self.client.post(reverse('editors.queue_moderated'), data_formset)
        eq_(r.status_code, 302)

    def test_skip(self):
        self.setup_actions(reviews.REVIEW_MODERATE_SKIP)

        # Make sure it's still there.
        r = self.client.get(reverse('editors.queue_moderated'))
        doc = pq(r.content)
        rows = doc('#reviews-flagged .review-flagged:not(.review-saved)')
        eq_(len(rows), 1)

    def test_remove(self):
        """ Make sure the editor tools can delete a review. """
        al = ActivityLog.objects.filter(action=amo.LOG.DELETE_REVIEW.id)
        al_start = al.count()
        self.setup_actions(reviews.REVIEW_MODERATE_DELETE)

        # Make sure it's removed from the queue.
        r = self.client.get(reverse('editors.queue_moderated'))
        doc = pq(r.content)
        rows = doc('#reviews-flagged .review-flagged:not(.review-saved)')
        eq_(len(rows), 0)

        r = self.client.get(reverse('editors.eventlog'))
        doc = pq(r.content)
        assert 'More details' in doc('table a').text()

        # Make sure it was actually deleted.
        eq_(len(Review.objects.filter(addon=1865)), 1)

        # One activity logged.
        al_end = ActivityLog.objects.filter(action=amo.LOG.DELETE_REVIEW.id)
        eq_(al_start + 1, al_end.count())

    def test_keep(self):
        """ Make sure the editor tools can remove flags and keep a review. """
        al = ActivityLog.objects.filter(action=amo.LOG.APPROVE_REVIEW.id)
        al_start = al.count()

        review = Review.objects.filter(addon=1865, editorreview=1)
        eq_(len(review), 1)

        self.setup_actions(reviews.REVIEW_MODERATE_KEEP)

        # Make sure it's removed from the queue.
        r = self.client.get(reverse('editors.queue_moderated'))
        doc = pq(r.content)
        rows = doc('#reviews-flagged .review-flagged:not(.review-saved)')
        eq_(len(rows), 0)

        review = Review.objects.filter(addon=1865)

        # Make sure it's NOT deleted...
        eq_(len(review), 2)

        # ...but it's no longer flagged
        eq_(len(review.filter(editorreview=1)), 0)

        # One activity logged.
        al_end = ActivityLog.objects.filter(action=amo.LOG.APPROVE_REVIEW.id)
        eq_(al_start + 1, al_end.count())

    def test_queue_count(self):
        r = self.client.get(reverse('editors.queue_moderated'))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        eq_(doc('.tabnav li a:eq(3)').text(), u'Moderated Review (1)')
        eq_(doc('.tabnav li a:eq(3)').attr('href'),
            reverse('editors.queue_moderated'))

    def test_breadcrumbs(self):
        r = self.client.get(reverse('editors.queue_moderated'))
        doc = pq(r.content)
        list_items = doc('ol.breadcrumbs li')
        eq_(list_items.length, 2)

        eq_(list_items.eq(0).find('a').text(), "Editor Tools")
        eq_(list_items.eq(1).text(), "Moderated Reviews")

    def test_no_reviews(self):
        Review.objects.all().delete()

        eq_(Review.objects.exists(), False)

        r = self.client.get(reverse('editors.queue_moderated'))
        eq_(r.status_code, 200)
        doc = pq(r.content)

        message = 'All reviews have been moderated. Good work!'
        eq_(doc('.no-results').text(), message)

        eq_(doc('.review-saved button').length, 1)  # Only show one button.


class TestPerformance(QueueTest):
    fixtures = ('base/users', 'editors/pending-queue', 'base/approvals')

    """Test the page at /editors/performance."""
    def setUp(self):
        super(TestPerformance, self).setUp()
        self.url_performance = reverse('editors.performance')

    def test_performance_chart(self):
        r = self.client.get(self.url_performance)
        doc = pq(r.content)

        data = {u'2010-08': {u'teamcount': 1, u'teamavg': u'1.0',
                             u'usercount': 1, u'teamamt': 1,
                             u'label': u'Aug 2010'}}

        eq_(json.loads(doc('#monthly').attr('data-chart')), data)


class SearchTest(EditorTest):

    def setUp(self):
        self.login_as_editor()

    def named_addons(self, request):
        return [row.data.addon_name
                for row in request.context['page'].object_list]

    def search(self, data):
        r = self.client.get(self.url, data=data)
        eq_(r.status_code, 200)
        eq_(r.context['search_form'].errors.as_text(), '')
        return r


class TestQueueSearch(SearchTest):
    fixtures = ('base/users', 'base/apps', 'base/appversion')

    def setUp(self):
        super(TestQueueSearch, self).setUp()
        self.url = reverse('editors.queue_nominated')
        create_addon_file('Not Admin Reviewed', '0.1',
                          amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED)
        create_addon_file('Admin Reviewed', '0.1',
                          amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED,
                          admin_review=True)
        create_addon_file('Justin Bieber Persona', '0.1',
                          amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED,
                          addon_type=amo.ADDON_THEME)
        create_addon_file('Justin Bieber Search Bar', '0.1',
                          amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED,
                          addon_type=amo.ADDON_SEARCH)
        create_addon_file('Bieber For Mobile', '0.1',
                          amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED,
                          application=amo.MOBILE)
        create_addon_file('Linux Widget', '0.1',
                          amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED,
                          platform=amo.PLATFORM_LINUX)
        create_addon_file('Mac Widget', '0.1',
                          amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED,
                          platform=amo.PLATFORM_MAC)

    def test_search_by_admin_reviewed(self):
        r = self.search({'admin_review': 1})
        eq_(self.named_addons(r), ['Admin Reviewed'])

    def test_queue_counts(self):
        r = self.search({'text_query': 'admin', 'per_page': 1})
        doc = pq(r.content)
        eq_(doc('.data-grid-top .num-results').text(),
            u'Results 1 \u2013 1 of 2')

    def test_search_by_addon_name(self):
        r = self.search({'text_query': 'admin'})
        eq_(sorted(self.named_addons(r)), ['Admin Reviewed',
                                           'Not Admin Reviewed'])

    def test_search_by_addon_in_locale(self):
        uni = 'フォクすけといっしょ'.decode('utf8')
        d = create_addon_file('Some Addon', '0.1',
                              amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED)
        a = Addon.objects.get(pk=d['addon'].id)
        a.name = {'ja': uni}
        a.save()
        r = self.client.get('/ja/' + self.url, data={'text_query': uni},
                            follow=True)
        eq_(r.status_code, 200)
        eq_(sorted(self.named_addons(r)), ['Some Addon'])

    def test_search_by_addon_author(self):
        d = create_addon_file('For Author Search', '0.1',
                              amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED)
        u = UserProfile.objects.create(username='fligtar',
                                       email='Fligtar@fligtar.com')
        au = AddonUser.objects.create(user=u, addon=d['addon'])
        author = AddonUser.objects.filter(id=au.id)
        for role in [amo.AUTHOR_ROLE_OWNER,
                     amo.AUTHOR_ROLE_DEV]:
            author.update(role=role)
            r = self.search({'text_query': 'fligtar@fligtar.com'})
            eq_(self.named_addons(r), ['For Author Search'])
        author.update(role=amo.AUTHOR_ROLE_VIEWER)
        r = self.search({'text_query': 'fligtar@fligtar.com'})
        eq_(self.named_addons(r), [])

    def test_search_by_supported_email_in_locale(self):
        d = create_addon_file('Some Addon', '0.1',
                              amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED)
        uni = 'フォクすけといっしょ@site.co.jp'.decode('utf8')
        a = Addon.objects.get(pk=d['addon'].id)
        a.support_email = {'ja': uni}
        a.save()
        r = self.client.get('/ja/' + self.url, data={'text_query': uni},
                            follow=True)
        eq_(r.status_code, 200)
        eq_(sorted(self.named_addons(r)), ['Some Addon'])

    def test_search_by_addon_type(self):
        r = self.search({'addon_type_ids': [amo.ADDON_THEME]})
        eq_(self.named_addons(r), ['Justin Bieber Persona'])

    def test_search_by_addon_type_any(self):
        r = self.search({'addon_type_ids': [amo.ADDON_ANY]})
        assert len(self.named_addons(r)) > 0

    def test_search_by_many_addon_types(self):
        r = self.search({'addon_type_ids': [amo.ADDON_THEME,
                                            amo.ADDON_SEARCH]})
        eq_(sorted(self.named_addons(r)),
            ['Justin Bieber Persona', 'Justin Bieber Search Bar'])

    def test_search_by_platform_mac(self):
        r = self.search({'platform_ids': [amo.PLATFORM_MAC.id]})
        eq_(r.status_code, 200)
        eq_(self.named_addons(r), ['Mac Widget'])

    def test_search_by_platform_linux(self):
        r = self.search({'platform_ids': [amo.PLATFORM_LINUX.id]})
        eq_(r.status_code, 200)
        eq_(self.named_addons(r), ['Linux Widget'])

    def test_search_by_platform_mac_linux(self):
        r = self.search({'platform_ids': [amo.PLATFORM_MAC.id,
                                          amo.PLATFORM_LINUX.id]})
        eq_(r.status_code, 200)
        eq_(sorted(self.named_addons(r)), ['Linux Widget', 'Mac Widget'])

    def test_preserve_multi_platform_files(self):
        for plat in (amo.PLATFORM_WIN, amo.PLATFORM_MAC):
            create_addon_file('Multi Platform', '0.1',
                              amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED,
                              platform=plat)
        r = self.search({'platform_ids': [amo.PLATFORM_WIN.id]})
        doc = pq(r.content)
        # Should not say Windows only:
        eq_(doc('table.data-grid tr').eq(1).children('td').eq(5).text(), '')

    def test_preserve_single_platform_files(self):
        create_addon_file('Windows', '0.1',
                          amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED,
                          platform=amo.PLATFORM_WIN)
        r = self.search({'platform_ids': [amo.PLATFORM_WIN.id]})
        doc = pq(r.content)
        eq_(doc('table.data-grid tr').eq(1).children('td').eq(5).text(),
            'Windows only')

    def test_search_by_app(self):
        r = self.search({'application_id': [amo.MOBILE.id]})
        eq_(r.status_code, 200)
        eq_(self.named_addons(r), ['Bieber For Mobile'])

    def test_preserve_multi_apps(self):
        for app in (amo.MOBILE, amo.FIREFOX):
            create_addon_file('Multi Application', '0.1',
                              amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED,
                              application=app)

        r = self.search({'application_id': [amo.MOBILE.id]})
        doc = pq(r.content)
        td = doc('table.data-grid tr').eq(2).children('td').eq(4)
        eq_(td.children().length, 2)
        eq_(td.children('.ed-sprite-firefox').length, 1)
        eq_(td.children('.ed-sprite-mobile').length, 1)

    def test_search_by_version_requires_app(self):
        r = self.client.get(self.url, data={'max_version': '3.6'})
        eq_(r.status_code, 200)
        # This is not the most descriptive message but it's
        # the easiest to show.  This missing app scenario is unlikely.
        eq_(r.context['search_form'].errors.as_text(),
            '* max_version\n  * Select a valid choice. 3.6 is not '
            'one of the available choices.')

    def test_search_by_app_version(self):
        d = create_addon_file('Bieber For Mobile 4.0b2pre', '0.1',
                              amo.STATUS_NOMINATED, amo.STATUS_UNREVIEWED,
                              application=amo.MOBILE)
        app = Application.objects.get(pk=amo.MOBILE.id)
        max = AppVersion.objects.get(application=app, version='4.0b2pre')
        (ApplicationsVersions.objects
         .filter(application=app, version=d['version']).update(max=max))
        r = self.search({'application_id': amo.MOBILE.id,
                         'max_version': '4.0b2pre'})
        eq_(self.named_addons(r), [u'Bieber For Mobile 4.0b2pre'])

    def test_age_of_submission(self):
        Version.objects.update(nomination=datetime.now() - timedelta(days=1))
        title = 'Justin Bieber Persona'
        bieber = (Version.objects.filter(addon__name__localized_string=title))
        # Exclude anything out of range:
        bieber.update(nomination=datetime.now() - timedelta(days=5))
        r = self.search({'waiting_time_days': 2})
        addons = self.named_addons(r)
        assert title not in addons, ('Unexpected results: %r' % addons)
        # Include anything submitted up to requested days:
        bieber.update(nomination=datetime.now() - timedelta(days=2))
        r = self.search({'waiting_time_days': 5})
        addons = self.named_addons(r)
        assert title in addons, ('Unexpected results: %r' % addons)
        # Special case: exclude anything under 10 days:
        bieber.update(nomination=datetime.now() - timedelta(days=8))
        r = self.search({'waiting_time_days': '10+'})
        addons = self.named_addons(r)
        assert title not in addons, ('Unexpected results: %r' % addons)
        # Special case: include anything 10 days and over:
        bieber.update(nomination=datetime.now() - timedelta(days=12))
        r = self.search({'waiting_time_days': '10+'})
        addons = self.named_addons(r)
        assert title in addons, ('Unexpected results: %r' % addons)

    def test_form(self):
        r = self.search({})
        doc = pq(r.content)
        eq_(doc('#id_application_id').attr('data-url'),
            reverse('editors.application_versions_json'))
        eq_(doc('#id_max_version option').text(),
            'Select an application first')
        r = self.search({'application_id': amo.MOBILE.id})
        doc = pq(r.content)
        eq_(doc('#id_max_version option').text(), '4.0b2pre 2.0a1pre 1.0')

    def test_application_versions_json(self):
        r = self.client.post(reverse('editors.application_versions_json'),
                             {'application_id': amo.MOBILE.id})
        eq_(r.status_code, 200)
        data = json.loads(r.content)
        eq_(data['choices'],
            [['', ''],
             ['4.0b2pre', '4.0b2pre'],
             ['2.0a1pre', '2.0a1pre'],
             ['1.0', '1.0']])


class TestQueueSearchVersionSpecific(SearchTest):

    def setUp(self):
        super(TestQueueSearchVersionSpecific, self).setUp()
        self.url = reverse('editors.queue_prelim')
        create_addon_file('Not Admin Reviewed', '0.1',
                          amo.STATUS_LITE, amo.STATUS_UNREVIEWED)
        create_addon_file('Justin Bieber Persona', '0.1',
                          amo.STATUS_LITE, amo.STATUS_UNREVIEWED,
                          addon_type=amo.ADDON_THEME)

    def test_age_of_submission(self):
        Version.objects.update(created=datetime.now() - timedelta(days=1))
        bieber = (Version.objects.filter(
                  addon__name__localized_string='Justin Bieber Persona'))
        # Exclude anything out of range:
        bieber.update(created=datetime.now() - timedelta(days=5))
        r = self.search({'waiting_time_days': 2})
        addons = self.named_addons(r)
        assert 'Justin Bieber Persona' not in addons, (
                                'Unexpected results: %r' % addons)
        # Include anything submitted up to requested days:
        bieber.update(created=datetime.now() - timedelta(days=2))
        r = self.search({'waiting_time_days': 4})
        addons = self.named_addons(r)
        assert 'Justin Bieber Persona' in addons, (
                                'Unexpected results: %r' % addons)
        # Special case: exclude anything under 10 days:
        bieber.update(created=datetime.now() - timedelta(days=8))
        r = self.search({'waiting_time_days': '10+'})
        addons = self.named_addons(r)
        assert 'Justin Bieber Persona' not in addons, (
                                'Unexpected results: %r' % addons)
        # Special case: include anything 10 days and over:
        bieber.update(created=datetime.now() - timedelta(days=12))
        r = self.search({'waiting_time_days': '10+'})
        addons = self.named_addons(r)
        assert 'Justin Bieber Persona' in addons, (
                                'Unexpected results: %r' % addons)


class ReviewBase(QueueTest):
    def setUp(self):
        super(ReviewBase, self).setUp()
        self.version = self.versions['Public']
        self.addon = self.version.addon
        self.editor = UserProfile.objects.get(email='editor@mozilla.com')
        self.editor.update(display_name='An editor')
        self.url = reverse('editors.review', args=[self.version.pk])


class TestReview(ReviewBase):
    def setUp(self):
        super(TestReview, self).setUp()
        AddonUser.objects.create(addon=self.addon,
                         user=UserProfile.objects.get(pk=999))

    def test_editor_required(self):
        response = self.client.get(self.url)
        eq_(response.status_code, 200)

    def test_not_anonymous(self):
        self.client.logout()
        response = self.client.get(self.url)
        eq_(response.status_code, 302)

    @patch_object(settings, 'DEBUG', False)
    def test_not_author(self):
        AddonUser.objects.create(addon=self.addon, user=self.editor)
        response = self.client.get(self.url)
        eq_(response.status_code, 302)

    def test_not_flags(self):
        response = self.client.get(self.url)
        eq_(len(response.context['flags']), 0)

    def test_flags(self):
        Review.objects.create(addon=self.addon, flag=True, user=self.editor)
        Review.objects.create(addon=self.addon, flag=False, user=self.editor)
        response = self.client.get(self.url)
        eq_(len(response.context['flags']), 1)

    def test_info_comments_requested(self):
        response = self.client.post(self.url, {'action': 'info'})
        eq_(response.context['form'].errors['comments'][0],
            'This field is required.')

    def test_info_requested(self):
        response = self.client.post(self.url, {'action': 'info',
                                               'comments': 'hello sailor'})
        eq_(response.status_code, 302)
        eq_(len(mail.outbox), 1)
        self.assertTemplateUsed(response, 'editors/emails/info.ltxt')

    def test_super_review_requested(self):
        response = self.client.post(self.url, {'action': 'super',
                                               'comments': 'hello sailor'})
        eq_(response.status_code, 302)
        eq_(len(mail.outbox), 2)
        self.assertTemplateUsed(response, 'editors/emails/author_super_review.ltxt')
        self.assertTemplateUsed(response, 'editors/emails/super_review.ltxt')

    def test_info_requested_canned_response(self):
        response = self.client.post(self.url, {'action': 'info',
                                               'comments': 'hello sailor',
                                               'canned_response': 'foo'})
        eq_(response.status_code, 302)
        eq_(len(mail.outbox), 1)
        self.assertTemplateUsed(response, 'editors/emails/info.ltxt')

    def test_notify(self):
        response = self.client.post(self.url, {'action': 'info',
                                               'comments': 'hello sailor',
                                               'notify': True})
        eq_(response.status_code, 302)
        eq_(EditorSubscription.objects.count(), 1)

    def test_no_notify(self):
        response = self.client.post(self.url, {'action': 'info',
                                               'comments': 'hello sailor'})
        eq_(response.status_code, 302)
        eq_(EditorSubscription.objects.count(), 0)

    def test_paging_none(self):
        response = self.client.get(self.url)
        eq_(response.context['paging'], {})

    def test_approvalnotes(self):
        self.version.update(approvalnotes='Testing 123')
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        doc = pq(response.content)
        eq_(len(doc('#approval-notes')), 1)
        eq_(doc('#approval-notes').next().text(), 'Testing 123')

    def test_page_title(self):
        response = self.client.get(self.url)
        eq_(response.status_code, 200)
        doc = pq(response.content)
        eq_(doc('title').text(),
            '%s :: Editor Tools :: Add-ons' % self.addon.name)

    def test_paging_num(self):
        response = self.client.get('%s?num=1' % self.url)
        eq_(response.context['paging']['prev'], False)
        eq_(response.context['paging']['next'], True)
        eq_(response.context['paging']['total'], 2)

        response = self.client.get('%s?num=2' % self.url)
        eq_(response.context['paging']['prev'], True)
        eq_(response.context['paging']['next'], False)

    def test_paging_error(self):
        response = self.client.get('%s?num=x' % self.url)
        eq_(response.status_code, 404)

    def test_files_shown(self):
        response = self.client.get(self.url)
        eq_(response.status_code, 200)

        validation = pq(response.content).find('#validation').next()
        eq_(validation.children().length, 1)

        eq_(validation.find('a').eq(0).text(), 'Public.xpi')

        eq_(validation.find('a').eq(1).text(), "Validation Results")
        eq_(validation.find('a').eq(2).text(), "View Contents")

        eq_(validation.find('a').length, 3)

    def test_no_items(self):
        response = self.client.get(self.url)
        eq_(pq(response.content).find('#file-history').next().text(),
            "No previous review entries could be found.")

    def test_listing_link(self):
        response = self.client.get(self.url)
        text = pq(response.content).find('#actions-addon li a').eq(0).text()
        eq_(text, "View Listing")

    def test_admin_links_as_admin(self):
        self.login_as_admin()
        response = self.client.get(self.url)

        doc = pq(response.content)

        admin = doc('#actions-admin')
        assert admin.length > 0

        a = admin.find('a').eq(0)
        eq_(a.text(), "Edit Add-on")
        assert "developers/addon/%s" % self.addon.slug in a.attr('href')

        a = admin.find('a').eq(1)
        eq_(a.text(), "Admin Page")
        assert "admin/addons/status/%s" % self.addon.id in a.attr('href')

    def test_admin_links_as_non_admin(self):
        self.login_as_editor()
        response = self.client.get(self.url)

        doc = pq(response.content)
        admin = doc('#actions-admin')
        eq_(admin.length, 0)

    def test_no_public(self):
        s = amo.STATUS_PUBLIC

        has_public = self.version.files.filter(status=s).exists()
        assert not has_public

        for version_file in self.version.files.all():
            version_file.status = amo.STATUS_PUBLIC
            version_file.save()

        has_public = self.version.files.filter(status=s).exists()
        assert has_public

        response = self.client.get(self.url)

        validation = pq(response.content).find('#validation').next()
        eq_(validation.find('a').eq(1).text(), "Validation Results")
        eq_(validation.find('a').eq(2).text(), "View Contents")

        eq_(validation.find('a').length, 3)

    def test_public_search(self):
        s = amo.STATUS_PUBLIC

        has_public = self.version.files.filter(status=s).exists()
        assert not has_public

        for version_file in self.version.files.all():
            version_file.status = amo.STATUS_PUBLIC
            version_file.save()

        has_public = self.version.files.filter(status=s).exists()
        assert has_public

        self.addon.type = amo.ADDON_SEARCH
        self.addon.save()

        eq_(self.addon.type, amo.ADDON_SEARCH)

        response = self.client.get(self.url)

        validation = pq(response.content).find('#validation').next()
        eq_(validation.find('a').eq(1).text(), "Validation Results")
        eq_(validation.find('a').eq(2).text(), "View Contents")

        eq_(validation.find('a').length, 3)

    def test_version_deletion(self):
        """
        Make sure that we still show review history for deleted versions.
        """
        # Add a new version to the add-on.
        self.addon_file(u'something', u'0.2', amo.STATUS_PUBLIC,
                        amo.STATUS_UNREVIEWED)
        v2 = self.versions['something']
        v2.addon = self.addon
        v2.save()

        eq_(self.addon.versions.count(), 2)

        url = lambda v: reverse('editors.review', args=[v.id])

        # Review both.
        for version in [v2, self.version]:
            version.files.all()[0].update(status=amo.STATUS_UNREVIEWED)
            d = dict(action='prelim', operating_systems='win',
                     applications='something', comments='something',
                     addon_files=[version.files.all()[0].pk])
            r = self.client.post(url(version), d)

        r = self.client.get(url(self.version))
        doc = pq(r.content)
        # View the history verify two versions:
        eq_(doc('table#review-files tr td:first-child').eq(0).text(), '0.2')
        eq_(doc('table#review-files tr td:first-child').eq(1).text(), '0.1')
        # Delete a version:
        v2.delete()
        # Verify two versions, one deleted:
        r = self.client.get(url(self.version))
        doc = pq(r.content)
        eq_(doc('table#review-files tr td:first-child').eq(0).text(),
            'Deleted version')
        eq_(doc('table#review-files tr td:first-child').eq(1).text(), '0.1')

    def test_eula_displayed(self):
        assert not self.addon.eula
        r = self.client.get(self.url)
        assert "View EULA" not in r.content

        self.addon.eula = "Test!"
        self.addon.save()
        r = self.client.get(self.url)
        assert "View EULA" in r.content

    def test_privacy_policy_displayed(self):
        assert not self.addon.privacy_policy
        r = self.client.get(self.url)
        assert "View Privacy Policy" not in r.content

        self.addon.privacy_policy = "Test!"
        self.addon.save()
        r = self.client.get(self.url)
        assert "View Privacy Policy" in r.content

    def test_breadcrumbs(self):
        r = self.client.get(self.url)
        doc = pq(r.content)
        list_items = doc('ol.breadcrumbs li')
        eq_(list_items.length, 3)

        eq_(list_items.eq(0).find('a').text(), "Editor Tools")
        eq_(list_items.eq(1).find('a').text(), "Pending Updates")

    def test_breadcrumbs_all(self):
        queues = {'Full Reviews': [3, 9],
                  'Preliminary Reviews': [1, 8],
                  'Pending Updates': [2, 4]}

        for text, queue_ids in queues.items():
            for qid in queue_ids:
                self.addon.update(status=qid)
                doc = pq(self.client.get(self.url).content)
                eq_(doc('ol.breadcrumbs li:eq(1)').text(), text)

    def test_viewing(self):
        r = self.client.post(reverse('editors.review_viewing'),
                             {'addon_id': self.addon.id })
        data = json.loads(r.content)
        eq_(data['current'], self.editor.id)
        eq_(data['current_name'], self.editor.name)
        eq_(data['is_user'], 1)

        # Now, login as someone else and test.
        self.login_as_admin()
        r = self.client.post(reverse('editors.review_viewing'),
                             {'addon_id': self.addon.id })
        data = json.loads(r.content)
        eq_(data['current'], self.editor.id)
        eq_(data['current_name'], self.editor.name)
        eq_(data['is_user'], 0)

    def test_no_compare_link(self):
        r = self.client.get(self.url)
        doc = pq(r.content)
        # By default there are 3 links, download file, validation and browse
        doc(len('.files a'), 3)

    def test_compare_link(self):
        Switch.objects.create(name='zamboni-file-viewer', active=1)
        version = Version.objects.create(addon=self.addon, version='0.2')
        version.created = datetime.today() + timedelta(days=1)
        version.save()

        first_file = self.addon.versions.order_by('created')[0].files.all()[0]
        first_file.status = amo.STATUS_PUBLIC
        first_file.save()

        url = reverse('editors.review', args=[version.pk])
        next_file = File.objects.create(version=version, status=amo.STATUS_PUBLIC)
        self.addon.update(_current_version=version)
        eq_(self.addon.current_version, version)
        r = self.client.get(url)
        doc = pq(r.content)

        assert r.context['show_diff']
        eq_(doc('.files a:last-child').text(), 'Compare With Public Version')
        eq_(doc('.files a:last-child').attr('href'),
            reverse('files.compare', args=(next_file.pk,
                                           first_file.pk)))


class TestReviewPreliminary(ReviewBase):

    def get_addon(self):
        return Addon.objects.get(pk=self.addon.pk)

    def setUp(self):
        super(TestReviewPreliminary, self).setUp()
        AddonUser.objects.create(addon=self.addon,
                                 user=UserProfile.objects.get(pk=999))

    def prelim_dict(self):
        return {'action': 'prelim', 'operating_systems': 'win',
                'applications': 'something', 'comments': 'something',
                'addon_files': [self.version.files.all()[0].pk]}

    def test_prelim_comments_requested(self):
        response = self.client.post(self.url, {'action': 'prelim'})
        eq_(response.context['form'].errors['comments'][0],
            'This field is required.')

    def test_prelim_from_lite(self):
        self.addon.update(status=amo.STATUS_LITE)
        self.version.files.all()[0].update(status=amo.STATUS_UNREVIEWED)
        response = self.client.post(self.url, self.prelim_dict())
        eq_(response.status_code, 302)
        eq_(self.get_addon().status, amo.STATUS_LITE)

    def test_prelim_from_lite_required(self):
        self.addon.update(status=amo.STATUS_LITE)
        response = self.client.post(self.url, {'action': 'prelim'})

        eq_(response.context['form'].errors['comments'][0],
            'This field is required.')

    def test_prelim_from_lite_no_files(self):
        self.addon.update(status=amo.STATUS_LITE)
        data = self.prelim_dict()
        del data['addon_files']
        response = self.client.post(self.url, data)

        eq_(response.context['form'].errors['addon_files'][0],
            'You must select some files.')

    def test_prelim_from_lite_wrong(self):
        self.addon.update(status=amo.STATUS_LITE)
        response = self.client.post(self.url, self.prelim_dict())

        eq_(response.context['form'].errors['addon_files'][0],
            'File Public.xpi is not pending review.')

    def test_prelim_from_lite_wrong_two(self):
        self.addon.update(status=amo.STATUS_LITE)
        data = self.prelim_dict()
        file = self.version.files.all()[0]
        for status in amo.STATUS_CHOICES:
            if status != amo.STATUS_UNREVIEWED:
                file.update(status=status)
                response = self.client.post(self.url, data)
                eq_(response.context['form'].errors['addon_files'][0],
                    'File Public.xpi is not pending review.')

    def test_prelim_from_lite_files(self):
        self.addon.update(status=amo.STATUS_LITE)
        self.client.post(self.url, data=self.prelim_dict())
        eq_(self.get_addon().status, amo.STATUS_LITE)

    def test_prelim_from_unreviewed(self):
        self.addon.update(status=amo.STATUS_UNREVIEWED)
        response = self.client.post(self.url, self.prelim_dict())
        eq_(response.status_code, 302)
        eq_(self.get_addon().status, amo.STATUS_LITE)

    def test_prelim_multiple_files(self):
        version = self.addon.versions.all()[0]
        file = version.files.all()[0]
        file.pk = None
        file.status = amo.STATUS_DISABLED
        file.save()
        self.addon.update(status=amo.STATUS_LITE)
        data = self.prelim_dict()
        data['addon_files'] = [file.pk]
        self.client.post(self.url, data)
        eq_([amo.STATUS_DISABLED, amo.STATUS_LISTED],
            [v.status for v in version.files.all().order_by('status')])

    def test_breadcrumbs(self):
        r = self.client.get(self.url)
        doc = pq(r.content)
        list_items = doc('ol.breadcrumbs li')
        eq_(list_items.length, 3)

        eq_(list_items.eq(0).find('a').text(), "Editor Tools")
        eq_(list_items.eq(1).find('a').text(), "Pending Updates")


class TestReviewPending(ReviewBase):

    def get_addon(self):
        return Addon.objects.get(pk=self.addon.pk)

    def setUp(self):
        super(TestReviewPending, self).setUp()
        self.addon.update(status=4)
        AddonUser.objects.create(addon=self.addon,
                                 user=UserProfile.objects.get(pk=999))
        self.file = File.objects.create(version=self.version,
                                        status=amo.STATUS_UNREVIEWED)

    def pending_dict(self):
        return {'action': 'public', 'operating_systems': 'win',
                'applications': 'something', 'comments': 'something',
                'addon_files': [v.pk for v in self.version.files.all()]}

    def test_pending_to_public(self):
        eq_(len(set([f.status for f in self.version.files.all()])), 2)
        response = self.client.post(self.url, self.pending_dict())
        eq_(response.status_code, 302)
        eq_(self.get_addon().status, amo.STATUS_PUBLIC)
        eq_(set([f.status for f in self.version.files.all()]), set([4]))

    def test_disabled_file(self):
        obj = File.objects.create(version=self.version,
                                  status=amo.STATUS_DISABLED)
        response = self.client.get(self.url, self.pending_dict())
        doc = pq(response.content)
        assert 'disabled' in doc('#file-%s' % obj.pk)[0].keys()
        assert 'disabled' not in doc('#file-%s' % self.file.pk)[0].keys()


class TestEditorMOTD(EditorTest):

    def test_change_motd(self):
        self.login_as_admin()
        r = self.client.post(reverse('editors.save_motd'),
                             {'motd': "Let's get crazy"})
        if r.context:
            eq_(r.context['form'].errors.as_text(), "")
        self.assertRedirects(r, reverse('editors.motd'))
        r = self.client.get(reverse('editors.motd'))
        doc = pq(r.content)
        eq_(doc('.daily-message p').text(), "Let's get crazy")

    def test_require_editor_to_view(self):
        r = self.client.get(reverse('editors.motd'))
        eq_(r.status_code, 302)

    def test_require_admin_to_change_motd(self):
        self.login_as_editor()
        r = self.client.post(reverse('editors.save_motd'),
                             {'motd': "I'm a sneaky editor"})
        eq_(r.status_code, 403)

    def test_editor_can_view_not_edit(self):
        set_config('editors_review_motd', 'Some announcement')
        self.login_as_editor()
        r = self.client.get(reverse('editors.motd'))
        doc = pq(r.content)
        eq_(doc('.daily-message p').text(), "Some announcement")
        eq_(r.context['form'], None)

    def test_form_errors(self):
        self.login_as_admin()
        r = self.client.post(reverse('editors.save_motd'), {})
        doc = pq(r.content)
        eq_(doc('#editor-motd .errorlist').text(), 'This field is required.')


class TestStatusFile(ReviewBase):

    def setUp(self):
        super(TestStatusFile, self).setUp()
        self.file = self.addon.current_version.files.all()[0]

    def test_status(self):
        for status in [amo.STATUS_UNREVIEWED, amo.STATUS_LITE]:
            self.addon.update(status=status)
            res = self.client.get(self.url)
            node = pq(res.content)('ul.files li:first-child')
            assert 'Pending Preliminary Review' in node.text()

    def test_status_full(self):
        for status in [amo.STATUS_NOMINATED, amo.STATUS_LITE_AND_NOMINATED,
                       amo.STATUS_PUBLIC]:
            self.addon.update(status=status)
            res = self.client.get(self.url)
            node = pq(res.content)('ul.files li:first-child')
            assert 'Pending Full Review' in node.text()

    def test_status_full_reviewed(self):
        version_file = self.addon.versions.all()[0].files.all()[0]
        version_file.update(status=amo.STATUS_PUBLIC)

        for status in [amo.STATUS_UNREVIEWED, amo.STATUS_LITE,
                       amo.STATUS_NOMINATED, amo.STATUS_LITE_AND_NOMINATED]:
            self.addon.update(status=status)
            res = self.client.get(self.url)
            node = pq(res.content)('ul.files li:first-child')
            assert 'Fully Reviewed' in node.text()

    def test_other(self):
        self.addon.update(status=amo.STATUS_BETA)
        res = self.client.get(self.url)
        node = pq(res.content)('ul.files li:first-child')
        assert unicode(amo.STATUS_CHOICES[self.file.status]) in node.text()
