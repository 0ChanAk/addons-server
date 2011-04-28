import shutil

import path
import mock

from django.conf import settings

import amo
from amo.tests.test_helpers import get_image_path
import paypal
import test_utils
from applications.models import Application, AppVersion
from addons.models import Addon, Charity
from devhub import forms
from files.models import FileUpload
from versions.models import ApplicationsVersions

from nose.tools import eq_


class TestNewAddonForm(test_utils.TestCase):

    def test_only_valid_uploads(self):
        f = FileUpload.objects.create(valid=False)
        form = forms.NewAddonForm({'upload': f.pk})
        assert 'upload' in form.errors

        f.validation = '{"errors": 0}'
        f.save()
        form = forms.NewAddonForm({'upload': f.pk})
        assert 'upload' not in form.errors


class TestContribForm(test_utils.TestCase):

    def test_neg_suggested_amount(self):
        form = forms.ContribForm({'suggested_amount': -10})
        assert not form.is_valid()
        eq_(form.errors['suggested_amount'][0],
            'Please enter a suggested amount greater than 0.')

    def test_max_suggested_amount(self):
        form = forms.ContribForm({'suggested_amount':
                            settings.MAX_CONTRIBUTION + 10})
        assert not form.is_valid()
        eq_(form.errors['suggested_amount'][0],
            'Please enter a suggested amount less than $%s.' %
            settings.MAX_CONTRIBUTION)


class TestCharityForm(test_utils.TestCase):

    def setUp(self):
        self.paypal_mock = mock.Mock()
        self.paypal_mock.return_value = (True, None)
        paypal.check_paypal_id = self.paypal_mock

    def test_always_new(self):
        # Editing a charity should always produce a new row.
        params = dict(name='name', url='http://url.com/', paypal='paypal')
        charity = forms.CharityForm(params).save()
        for k, v in params.items():
            eq_(getattr(charity, k), v)
        assert charity.id

        # Get a fresh instance since the form will mutate it.
        instance = Charity.objects.get(id=charity.id)
        params['name'] = 'new'
        new_charity = forms.CharityForm(params, instance=instance).save()
        for k, v in params.items():
            eq_(getattr(new_charity, k), v)

        assert new_charity.id != charity.id


class TestCompatForm(test_utils.TestCase):
    fixtures = ['base/apps', 'base/addon_3615']

    def test_mozilla_app(self):
        moz = amo.MOZILLA
        appver = AppVersion.objects.create(application_id=moz.id)
        v = Addon.objects.get(id=3615).current_version
        ApplicationsVersions(application_id=moz.id, version=v,
                             min=appver, max=appver).save()
        fs = forms.CompatFormSet(None, queryset=v.apps.all())
        apps = [f.app for f in fs.forms]
        assert moz in apps


class TestPreviewForm(test_utils.TestCase):
    fixtures = ['base/addon_3615']

    @mock.patch('amo.models.ModelBase.update')
    def test_preview_modified(self, update_mock):
        addon = Addon.objects.get(pk=3615)
        name = 'transparent.png'
        form = forms.PreviewForm({'caption': 'test','upload_hash': name,
                                  'position': 1})
        dest = path.path(settings.TMP_PATH) / 'preview' / name
        shutil.copyfile(get_image_path(name), dest)
        assert form.is_valid()
        form.save(addon)
        assert update_mock.called
