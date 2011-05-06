# -*- coding: utf-8 -*-
import os
import mimetypes
import shutil
import tempfile

from django.conf import settings
from django.core.cache import cache

from mock import Mock, patch_object
from nose.tools import eq_
import test_utils

from amo.urlresolvers import reverse
from files.helpers import FileViewer, DiffHelper
from files.models import File

root = os.path.join(settings.ROOT, 'apps/files/fixtures/files')
dictionary = '%s/dictionary-test.xpi' % root
recurse = '%s/recurse.xpi' % root
search = '%s/search.xml' % root


class TestFileHelper(test_utils.TestCase):

    def setUp(self):
        file_obj = Mock()
        file_obj.id = file_obj.pk = 1
        file_obj.file_path = dictionary

        self.old_tmp = settings.TMP_PATH
        settings.TMP_PATH = tempfile.mkdtemp()

        self.viewer = FileViewer(file_obj)

    def tearDown(self):
        self.viewer.cleanup()
        settings.TMP_PATH = self.old_tmp

    def test_files_not_extracted(self):
        eq_(self.viewer.is_extracted, False)

    def test_files_extracted(self):
        self.viewer.extract()
        eq_(self.viewer.is_extracted, True)

    def test_recurse_extract(self):
        self.viewer.src = recurse
        self.viewer.extract()
        eq_(self.viewer.is_extracted, True)

    def test_recurse_contents(self):
        self.viewer.src = recurse
        self.viewer.extract()
        files = self.viewer.get_files()
        nm = ['recurse/recurse.xpi/chrome/test-root.txt',
              'recurse/somejar.jar/recurse/recurse.xpi/chrome/test.jar',
              'recurse/somejar.jar/recurse/recurse.xpi/chrome/test.jar/test']
        for name in nm:
            eq_(name in files, True, 'File %r not extracted' % name)

    def test_cleanup(self):
        self.viewer.extract()
        self.viewer.cleanup()
        eq_(self.viewer.is_extracted, False)

    def test_isbinary(self):
        binary = self.viewer.is_binary
        for f in ['foo.rdf', 'foo.xml', 'foo.js', 'foo.py'
                  'foo.html', 'foo.txt', 'foo.dtd', 'foo.xul',
                  'foo.properties', 'foo.json', 'foo.src']:
            m, encoding = mimetypes.guess_type(f)
            assert not binary(m, f), '%s should not be binary' % f

        for f in ['foo.dtd', 'foo.xul', 'foo.properties']:
            m, encoding = mimetypes.guess_type(f)
            assert not binary(None, f), '%s should not be binary' % f

        for f in ['foo.png', 'foo.gif', 'foo.xls', 'foo.dic']:
            m, encoding = mimetypes.guess_type(f)
            assert binary(m, f), '%s should be binary' % f

    def test_truncate(self):
        truncate = self.viewer.truncate
        for x, y in (['foo.rdf', 'foo.rdf'],
                     ['somelongfilename.rdf', 'somelongfilenam...rdf'],
                     [u'unicode삮.txt', u'unicode\uc0ae.txt'],
                     [u'unicodesomelong삮.txt', u'unicodesomelong...txt'],
                     ['somelongfilename.somelongextension',
                      'somelongfilenam...somelonge..'],):
            eq_(truncate(x), y)

    def test_get_files_not_extracted(self):
        assert not self.viewer.get_files()

    def test_get_files_size(self):
        self.viewer.extract()
        files = self.viewer.get_files()
        eq_(len(files), 14)

    def test_get_files_directory(self):
        self.viewer.extract()
        files = self.viewer.get_files()
        eq_(files['install.js']['directory'], False)
        eq_(files['install.js']['binary'], False)
        eq_(files['__MACOSX']['directory'], True)
        eq_(files['__MACOSX']['binary'], True)

    def test_url_file(self):
        self.viewer.extract()
        files = self.viewer.get_files()
        url = reverse('files.list', args=[self.viewer.file.id,
                                           'install.js'])
        assert files['install.js']['url'].endswith(url)

    def test_get_files_depth(self):
        self.viewer.extract()
        files = self.viewer.get_files()
        eq_(files['dictionaries/license.txt']['depth'], 1)

    def test_bom(self):
        dest = tempfile.mkstemp()[1]
        open(dest, 'w').write('foo'.encode('utf-16'))
        eq_(self.viewer.read_file({'full': dest, 'size': 1}), (u'foo', ''))

    def test_file_order(self):
        self.viewer.extract()
        dest = self.viewer.dest
        open(os.path.join(dest, 'chrome.manifest'), 'w')
        subdir = os.path.join(dest, 'chrome')
        os.mkdir(subdir)
        open(os.path.join(subdir, 'foo'), 'w')
        cache.clear()
        files = self.viewer.get_files().keys()
        rt = files.index(u'chrome')
        eq_(files[rt:rt + 3], [u'chrome', u'chrome/foo', u'chrome.manifest'])

    @patch_object(settings._wrapped, 'FILE_VIEWER_SIZE_LIMIT', 5)
    def test_file_size(self):
        self.viewer.extract()
        files = self.viewer.get_files()
        res = self.viewer.read_file(files.get('install.js'))
        eq_(res[0], '')
        assert res[1].startswith('File size is')

    def test_default(self):
        eq_(self.viewer.get_default(None), 'install.rdf')

class TestSearchEngineHelper(test_utils.TestCase):
    fixtures = ['base/addon_4594_a9']

    def setUp(self):
        self.file_one = File.objects.get(pk=25753)
        self.viewer = FileViewer(self.file_one)

        if not os.path.exists(os.path.dirname(self.viewer.src)):
            os.makedirs(os.path.dirname(self.viewer.src))
            open(self.viewer.src, 'w')

    def tearDown(self):
        self.viewer.cleanup()

    def test_is_search_engine(self):
        assert self.viewer.is_search_engine

    def test_extract_search_engine(self):
        self.viewer.extract()
        assert os.path.exists(self.viewer.dest)

    def test_default(self):
        self.viewer.extract()
        eq_(self.viewer.get_default(None), 'a9.xml')


class TestDiffSearchEngine(test_utils.TestCase):

    def setUp(self):
        src = os.path.join(settings.ROOT, search)

        file_one = Mock()
        file_one.id = file_one.pk = 1
        file_one.file_path = src
        file_one.filename = 'search.xml'

        file_two = Mock()
        file_two.id = file_two.pk = 2
        file_two.file_path = src
        file_two.filename = 'search.xml'

        self.helper = DiffHelper(file_one, file_two)
        self.helper.file_one.is_search_engine = True
        self.helper.file_two.is_search_engine = True

    def tearDown(self):
        self.helper.cleanup()

    def test_diff_search(self):
        self.helper.extract()
        shutil.move(os.path.join(self.helper.file_two.dest, 'search.xml'),
                    os.path.join(self.helper.file_two.dest, 's-20010101.xml'))
        assert self.helper.select('search.xml')


class TestDiffHelper(test_utils.TestCase):

    def setUp(self):
        src = os.path.join(settings.ROOT, dictionary)

        file_one = Mock()
        file_one.id = file_one.pk = 1
        file_one.file_path = src

        file_two = Mock()
        file_two.id = file_two.pk = 2
        file_two.file_path = src

        self.helper = DiffHelper(file_one, file_two)

    def tearDown(self):
        self.helper.cleanup()

    def test_files_not_extracted(self):
        eq_(self.helper.is_extracted, False)

    def test_files_extracted(self):
        self.helper.extract()
        eq_(self.helper.is_extracted, True)

    def test_get_files(self):
        eq_(self.helper.file_one.get_files(),
            self.helper.get_files(self.helper.file_one))

    def test_diffable(self):
        self.helper.extract()
        self.helper.select('install.js')
        assert self.helper.is_diffable()

    def test_diffable_one_missing(self):
        self.helper.extract()
        os.remove(os.path.join(self.helper.file_two.dest, 'install.js'))
        self.helper.select('install.js')
        assert not self.helper.is_diffable()
        eq_(unicode(self.helper.status),
            'install.js does not exist in file 2.')

    def test_diffable_both_missing(self):
        self.helper.extract()
        self.helper.select('foo.js')
        assert not self.helper.is_diffable()

    def test_diffable_one_binary_same(self):
        self.helper.extract()
        self.helper.select('install.js')
        self.helper.one['binary'] = True
        assert self.helper.is_binary()
        assert not self.helper.is_different()

    def test_diffable_one_binary_diff(self):
        self.helper.extract()
        self.change(self.helper.file_one.dest, 'asd')
        cache.clear()
        self.helper.select('install.js')
        self.helper.one['binary'] = True
        assert self.helper.is_binary()
        assert self.helper.is_different()

    def test_diffable_two_binary_diff(self):
        self.helper.extract()
        self.change(self.helper.file_one.dest, 'asd')
        self.change(self.helper.file_two.dest, 'asd123')
        cache.clear()
        self.helper.select('install.js')
        self.helper.one['binary'] = True
        self.helper.two['binary'] = True
        assert self.helper.is_binary()
        assert self.helper.is_different()

    def test_diffable_one_directory(self):
        self.helper.extract()
        self.helper.select('install.js')
        self.helper.one['directory'] = True
        assert not self.helper.is_diffable()
        eq_(unicode(self.helper.status),
            'install.js is a directory in file 1.')

    def change(self, file, text):
        path = os.path.join(file, 'install.js')
        data = open(path, 'r').read()
        data += text
        open(path, 'w').write(data)
