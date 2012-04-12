# -*- coding: utf-8 -*-
import calendar
from decimal import Decimal
import json
import jwt
import time

from django.conf import settings

import fudge
from fudge.inspector import arg
import mock
from nose.tools import eq_
from pyquery import PyQuery as pq
import waffle.models

from addons.models import Addon
import amo
import amo.tests
from amo.urlresolvers import reverse
from paypal import PaypalError
from stats.models import Contribution
from users.models import UserProfile

from mkt.inapp_pay.models import InappPayment, InappConfig, InappPayLog


class PaymentTest(amo.tests.TestCase):
    fixtures = ['webapps/337141-steamcube', 'base/users']

    def setUp(self):
        self.app = self.get_app()
        cfg = self.inapp_config = InappConfig(addon=self.app,
                                              status=amo.INAPP_STATUS_ACTIVE)
        cfg.public_key = self.app_id = InappConfig.generate_public_key()
        cfg.private_key = self.app_secret = InappConfig.generate_private_key()
        cfg.save()
        self.app.paypal_id = 'app-dev-paypal@theapp.com'
        self.app.save()

    def get_app(self):
        return Addon.objects.get(pk=337141)

    def make_contrib(self):
        payload = self.payload()
        uuid_ = '12345'
        return Contribution.objects.create(
                    addon_id=self.app.pk, amount=payload['request']['price'],
                    source='', source_locale='en-US',
                    currency=payload['request']['currency'],
                    uuid=uuid_, type=amo.CONTRIB_INAPP_PENDING,
                    paykey='some-paykey', user=self.user)

    def make_payment(self, contrib=None):
        app_payment = self.payload()
        if not contrib:
            contrib = self.make_contrib()
        return InappPayment.objects.create(
                            config=self.inapp_config,
                            contribution=contrib,
                            name=app_payment['request']['name'],
                            description=app_payment['request']['description'],
                            app_data=app_payment['request']['productdata'])

    def payload(self, app_id=None, exp=None, iat=None):
        if not app_id:
            app_id = self.app_id
        if not iat:
            iat = calendar.timegm(time.gmtime())
        if not exp:
            exp = iat + 3600  # expires in 1 hour
        return {
            'iss': app_id,
            'aud': settings.INAPP_MARKET_ID,
            'typ': 'mozilla/payments/pay/v1',
            'exp': exp,
            'iat': iat,
            'request': {
                'price': '0.99',
                'currency': 'USD',
                'name': 'My bands latest album',
                'description': '320kbps MP3 download, DRM free!',
                'productdata': 'my_product_id=1234'
            }
        }

    def request(self, app_secret=None, payload=None, **payload_kw):
        if not app_secret:
            app_secret = self.app_secret
        if not payload:
            payload = json.dumps(self.payload(**payload_kw))
        encoded = jwt.encode(payload, app_secret, algorithm='HS256')
        return unicode(encoded)  # django always passes unicode


class PaymentViewTest(PaymentTest):

    def setUp(self):
        super(PaymentViewTest, self).setUp()
        waffle.models.Switch.objects.create(name='in-app-payments-ui',
                                            active=True)
        self.user = UserProfile.objects.get(email='regular@mozilla.com')
        assert self.client.login(username='regular@mozilla.com',
                                 password='password')


class TestPayStart(PaymentViewTest):

    def test_missing_pay_request_on_start(self):
        rp = self.client.get(reverse('inapp_pay.pay_start'))
        eq_(rp.status_code, 400)

    def test_pay_start(self):
        payload = self.payload()
        req = self.request(payload=json.dumps(payload))
        rp = self.client.get(reverse('inapp_pay.pay_start'),
                             data=dict(req=req))
        eq_(rp.status_code, 200)
        assert 'x-frame-options' not in rp, "Can't deny with x-frame-options"
        # TODO(Kumar) UI is still in the works here.

        log = InappPayLog.objects.get()
        eq_(log.action, InappPayLog._actions['PAY_START'])
        eq_(log.config.pk, self.inapp_config.pk)
        assert log.session_key, 'Unexpected session_key: %r' % log.session_key

    def test_pay_start_error(self):
        rp = self.client.get(reverse('inapp_pay.pay_start'),
                             data=dict(req=self.request(app_secret='invalid')))
        eq_(rp.status_code, 200)
        doc = pq(rp.content)
        eq_(doc('h3').text(), 'Payment Error')

        log = InappPayLog.objects.get()
        eq_(log.action, InappPayLog._actions['EXCEPTION'])
        eq_(log.app_public_key, self.inapp_config.public_key)
        eq_(log.exception, InappPayLog._exceptions['RequestVerificationError'])
        assert log.session_key, 'Unexpected session_key: %r' % log.session_key

    @mock.patch.object(settings, 'INAPP_VERBOSE_ERRORS', True)
    def test_verbose_error(self):
        rp = self.client.get(reverse('inapp_pay.pay_start'),
                             data=dict(req=self.request(app_secret='invalid')))
        eq_(rp.status_code, 200)
        self.assertContains(rp, 'RequestVerificationError')


class TestPay(PaymentViewTest):

    def setUp(self):
        super(TestPay, self).setUp()
        self.complete_url = reverse('inapp_pay.pay_done',
                                    args=[self.inapp_config.pk, 'complete'])
        self.cancel_url = reverse('inapp_pay.pay_done',
                                  args=[self.inapp_config.pk, 'cancel'])
        self.upatch = mock.patch('mkt.inapp_pay.tasks.urlopen')
        self.upatch.start()

    def tearDown(self):
        super(TestPay, self).tearDown()
        self.upatch.stop()

    def assert_payment_done(self, payload, contrib_type):
        cnt = Contribution.objects.get(addon=self.app)
        eq_(cnt.addon.pk, self.app.pk)
        eq_(cnt.type, contrib_type)
        eq_(cnt.amount, Decimal(payload['request']['price']))
        eq_(cnt.currency, payload['request']['currency'])

        pmt = InappPayment.objects.get(contribution=cnt)
        eq_(pmt.config, self.inapp_config)
        eq_(pmt.name, payload['request']['name'])
        eq_(pmt.description, payload['request']['description'])
        eq_(pmt.app_data, payload['request']['productdata'])

    def test_missing_pay_request(self):
        rp = self.client.post(reverse('inapp_pay.pay'))
        eq_(rp.status_code, 400)

    def test_invalid_pay_request(self):
        rp = self.client.post(reverse('inapp_pay.pay'),
                              data=dict(req=self.request(app_id='unknown')))
        eq_(rp.status_code, 200)
        doc = pq(rp.content)
        eq_(doc('h3').text(), 'Payment Error')

    @fudge.patch('paypal.get_paykey')
    def test_paykey_exception(self, get_paykey):
        get_paykey.expects_call().raises(PaypalError())
        res = self.client.post(reverse('inapp_pay.pay'),
                               data=dict(req=self.request()))
        self.assertContains(res, 'Payment Error')
        eq_(InappPayLog.objects.get().action,
            InappPayLog._actions['PAY_ERROR'])

    @mock.patch.object(settings, 'INAPP_VERBOSE_ERRORS', True)
    @fudge.patch('paypal.get_paykey')
    def test_verbose_paypal_error(self, get_paykey):
        get_paykey.expects_call().raises(PaypalError())
        res = self.client.post(reverse('inapp_pay.pay'),
                               data=dict(req=self.request()))
        self.assertContains(res, 'PaypalError')

    @fudge.patch('paypal.get_paykey')
    def test_ok_no_preauth(self, get_paykey):
        payload = self.payload()
        (get_paykey.expects_call()
                   .with_matching_args(addon_id=self.app.pk,
                                       amount=payload['request']['price'],
                                       currency=payload['request']['currency'],
                                       email=self.app.paypal_id)
                   .returns(['some-pay-key', '']))
        req = self.request(payload=json.dumps(payload))
        res = self.client.post(reverse('inapp_pay.pay'), dict(req=req))
        assert 'some-pay-key' in res['Location'], (
                                'Unexpected redirect: %s' % res['Location'])

        log = InappPayLog.objects.get()
        eq_(log.action, InappPayLog._actions['PAY'])
        eq_(log.config.pk, self.inapp_config.pk)

        self.assert_payment_done(payload, amo.CONTRIB_INAPP_PENDING)

    @fudge.patch('paypal.check_purchase')
    @fudge.patch('paypal.get_paykey')
    @fudge.patch('mkt.inapp_pay.tasks.notify_app')
    def test_preauth_ok(self, check_purchase, get_paykey, notify_app):
        payload = self.payload()

        get_paykey.expects_call().returns(['some-pay-key', 'COMPLETED'])
        check_purchase.expects_call().returns('COMPLETED')
        notify_app.expects('delay').with_args(amo.INAPP_NOTICE_PAY,
                                              arg.any())  # payment ID to-be

        req = self.request(payload=json.dumps(payload))
        self.client.post(reverse('inapp_pay.pay'), dict(req=req))

        logs = InappPayLog.objects.all().order_by('created')
        eq_(logs[0].action, InappPayLog._actions['PAY'])
        eq_(logs[1].action, InappPayLog._actions['PAY_COMPLETE'])

        self.assert_payment_done(payload, amo.CONTRIB_INAPP)

    @fudge.patch('paypal.check_purchase')
    @fudge.patch('paypal.get_paykey')
    def test_unverified_preauth(self, check_purchase, get_paykey):
        get_paykey.expects_call().returns(['some-pay-key', 'COMPLETED'])
        check_purchase.expects_call().returns('')  # unverified preauth
        res = self.client.post(reverse('inapp_pay.pay'),
                               dict(req=self.request()))
        assert 'some-pay-key' in res['Location'], (
                                'Unexpected redirect: %s' % res['Location'])
        eq_(Contribution.objects.get().type, amo.CONTRIB_INAPP_PENDING)

    @fudge.patch('mkt.inapp_pay.tasks.notify_app')
    def test_pay_complete(self, notify_app):
        cnt = self.make_contrib()
        payment = self.make_payment(contrib=cnt)
        notify_app.expects('delay').with_args(amo.INAPP_NOTICE_PAY,
                                              payment.pk)
        res = self.client.get(self.complete_url, {'uuid': cnt.uuid})
        self.assertContains(res, 'Payment received')
        cnt = Contribution.objects.get(pk=cnt.pk)
        eq_(cnt.type, amo.CONTRIB_INAPP)
        eq_(InappPayLog.objects.get().action,
            InappPayLog._actions['PAY_COMPLETE'])

    @fudge.patch('mkt.inapp_pay.tasks.notify_app')
    def test_pay_cancel(self, notify_app):
        cnt = self.make_contrib()
        self.make_payment(contrib=cnt)
        res = self.client.get(self.cancel_url, {'uuid': cnt.uuid})
        self.assertContains(res, 'Payment canceled')
        cnt = Contribution.objects.get(pk=cnt.pk)
        eq_(cnt.type, amo.CONTRIB_INAPP_PENDING)
        eq_(InappPayLog.objects.get().action,
            InappPayLog._actions['PAY_CANCEL'])

    def test_invalid_contrib_uuid(self):
        res = self.client.get(self.complete_url, {'uuid': 'invalid-uuid'})
        self.assertContains(res, 'Payment Error')

    def test_non_ascii_invalid_uuid(self):
        res = self.client.get(self.complete_url, {'uuid': u'Азәрбајҹан'})
        self.assertContains(res, 'Payment Error')

    def test_missing_uuid(self):
        res = self.client.get(self.complete_url)
        self.assertContains(res, 'Payment Error')
