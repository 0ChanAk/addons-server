from django.core import mail

from nose.tools import eq_

import amo.tests
from amo.urlresolvers import reverse
from access.models import GroupUser
from addons.tests.test_views import TestMobile
from devhub.models import ActivityLog
from reviews.models import Review, ReviewFlag


class ReviewTest(amo.tests.TestCase):
    fixtures = ['base/apps', 'reviews/dev-reply.json', 'base/admin']


class TestViews(ReviewTest):

    def test_dev_reply(self):
        url = reverse('reviews.detail', args=['a1865', 218468])
        r = self.client.get(url)
        eq_(r.status_code, 200)

    def test_404_user_page(self):
        url = reverse('reviews.user', args=['a1865', 233452342])
        r = self.client.get(url)
        eq_(r.status_code, 404)

    def test_feed(self):
        url = reverse('reviews.list.rss', args=['a1865'])
        r = self.client.get(url)
        eq_(r.status_code, 200)


class TestFlag(ReviewTest):

    def setUp(self):
        self.url = reverse('reviews.flag', args=['a1865', 218468])
        self.client.login(username='jbalogh@mozilla.com', password='password')

    def test_no_login(self):
        self.client.logout()
        response = self.client.post(self.url)
        eq_(response.status_code, 401)

    def test_new_flag(self):
        response = self.client.post(self.url, {'flag': ReviewFlag.SPAM})
        eq_(response.status_code, 200)
        eq_(response.content, '{"msg": "Thanks; this review has been '
                                       'flagged for editor approval."}')
        eq_(ReviewFlag.objects.filter(flag=ReviewFlag.SPAM).count(), 1)
        eq_(Review.objects.filter(editorreview=True).count(), 1)

    def test_update_flag(self):
        response = self.client.post(self.url, {'flag': ReviewFlag.SPAM})
        eq_(response.status_code, 200)
        eq_(ReviewFlag.objects.filter(flag=ReviewFlag.SPAM).count(), 1)
        eq_(Review.objects.filter(editorreview=True).count(), 1)

        response = self.client.post(self.url, {'flag': ReviewFlag.LANGUAGE})
        eq_(response.status_code, 200)
        eq_(ReviewFlag.objects.filter(flag=ReviewFlag.LANGUAGE).count(), 1)
        eq_(ReviewFlag.objects.count(), 1)
        eq_(Review.objects.filter(editorreview=True).count(), 1)

    def test_flag_with_note(self):
        response = self.client.post(self.url,
                                    {'flag': ReviewFlag.OTHER, 'note': 'xxx'})
        eq_(response.status_code, 200)
        eq_(ReviewFlag.objects.filter(flag=ReviewFlag.OTHER).count(),
            1)
        eq_(ReviewFlag.objects.count(), 1)
        eq_(ReviewFlag.objects.get(flag=ReviewFlag.OTHER).note, 'xxx')
        eq_(Review.objects.filter(editorreview=True).count(), 1)

    def test_bad_flag(self):
        response = self.client.post(self.url, {'flag': 'xxx'})
        eq_(response.status_code, 400)
        eq_(Review.objects.filter(editorreview=True).count(), 0)


class TestDelete(ReviewTest):

    def setUp(self):
        self.url = reverse('reviews.delete', args=['a1865', 218207])
        self.client.login(username='jbalogh@mozilla.com', password='password')

    def test_no_login(self):
        self.client.logout()
        response = self.client.post(self.url)
        eq_(response.status_code, 401)

    def test_no_perms(self):
        GroupUser.objects.all().delete()
        response = self.client.post(self.url)
        eq_(response.status_code, 403)

    def test_404(self):
        url = reverse('reviews.delete', args=['a1865', 0])
        response = self.client.post(url)
        eq_(response.status_code, 404)

    def test_delete_review_with_dev_reply(self):
        cnt = Review.objects.count()
        response = self.client.post(self.url)
        eq_(response.status_code, 200)
        # Two are gone since we deleted a review with a reply.
        eq_(Review.objects.count(), cnt - 2)

    def test_delete_success(self):
        Review.objects.update(reply_to=None)
        cnt = Review.objects.count()
        response = self.client.post(self.url)
        eq_(response.status_code, 200)
        eq_(Review.objects.count(), cnt - 1)


class TestCreate(ReviewTest):

    def setUp(self):
        self.add = reverse('reviews.add', args=['a1865'])
        self.client.login(username='root_x@ukr.net', password='password')
        self.qs = Review.objects.filter(addon=1865)
        self.log_count = ActivityLog.objects.count

    def test_no_rating(self):
        r = self.client.post(self.add, {'body': 'no rating'})
        self.assertFormError(r, 'form', 'rating', 'This field is required.')

        eq_(len(mail.outbox), 0)

    def test_review_success(self):
        old_cnt = self.qs.count()
        log_count = self.log_count()
        r = self.client.post(self.add, {'body': 'xx', 'rating': 3})
        self.assertRedirects(r, reverse('reviews.list', args=['a1865']),
                             status_code=302)
        eq_(self.qs.count(), old_cnt + 1)
        # We should have an ADD_REVIEW entry now.
        eq_(self.log_count(), log_count + 1)

        eq_(len(mail.outbox), 1)
        self.assertTemplateUsed(r, 'reviews/emails/add_review.ltxt')

    def test_new_reply(self):
        self.client.login(username='trev@adblockplus.org', password='password')
        Review.objects.filter(reply_to__isnull=False).delete()
        url = reverse('reviews.reply', args=['a1865', 218207])
        r = self.client.post(url, {'body': 'unst unst'})
        self.assertRedirects(r,
                             reverse('reviews.detail', args=['a1865', 218207]))
        eq_(self.qs.filter(reply_to=218207).count(), 1)

        eq_(len(mail.outbox), 1)
        self.assertTemplateUsed(r, 'reviews/emails/reply_review.ltxt')

    def test_double_reply(self):
        self.client.login(username='trev@adblockplus.org', password='password')
        url = reverse('reviews.reply', args=['a1865', 218207])
        r = self.client.post(url, {'body': 'unst unst'})
        self.assertRedirects(r,
                             reverse('reviews.detail', args=['a1865', 218207]))
        eq_(self.qs.filter(reply_to=218207).count(), 1)
        review = Review.objects.get(id=218468)
        eq_('%s' % review.body, 'unst unst')


class TestEdit(ReviewTest):

    def setUp(self):
        self.client.login(username='root_x@ukr.net', password='password')

    def test_edit(self):
        url = reverse('reviews.edit', args=['a1865', 218207])
        r = self.client.post(url, {'rating': 2, 'body': 'woo woo'},
                             X_REQUESTED_WITH='XMLHttpRequest')
        eq_(r.status_code, 200)
        eq_('%s' % Review.objects.get(id=218207).body, 'woo woo')

    def test_edit_not_owner(self):
        url = reverse('reviews.edit', args=['a1865', 218468])
        r = self.client.post(url, {'rating': 2, 'body': 'woo woo'},
                             X_REQUESTED_WITH='XMLHttpRequest')
        eq_(r.status_code, 403)

    def test_edit_reply(self):
        self.client.login(username='trev@adblockplus.org', password='password')
        url = reverse('reviews.edit', args=['a1865', 218468])
        r = self.client.post(url, {'title': 'fo', 'body': 'shizzle'},
                             X_REQUESTED_WITH='XMLHttpRequest')
        eq_(r.status_code, 200)
        review = Review.objects.get(id=218468)
        eq_('%s' % review.title, 'fo')
        eq_('%s' % review.body, 'shizzle')


class TestMobileReviews(TestMobile):
    fixtures = ['base/apps', 'reviews/dev-reply.json']

    def test_mobile(self):
        r = self.client.get(reverse('reviews.list', args=['a1865']))
        eq_(r.status_code, 200)
        self.assertTemplateUsed(r, 'reviews/mobile/review_list.html')
