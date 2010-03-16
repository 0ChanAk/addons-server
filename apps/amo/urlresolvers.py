import hashlib
import urllib
from urlparse import urlparse

from django.conf import settings
from django.core.urlresolvers import reverse as django_reverse
from django.utils.thread_support import currentThread
from django.utils.translation.trans_real import parse_accept_lang_header

import amo.models


# Thread-local storage for URL prefixes.  Access with {get,set}_url_prefix.
_prefixes = {}


def set_url_prefix(prefix):
    """Set ``prefix`` for the current thread."""
    _prefixes[currentThread()] = prefix


def get_url_prefix():
    """Get the prefix for the current thread, or None."""
    return _prefixes.get(currentThread())


def reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None,
            current_app=None):
    """Wraps django's reverse to prepend the correct locale and app."""
    prefixer = get_url_prefix()
    # Blank out the script prefix since we add that in prefixer.fix().
    if prefixer:
        prefix = prefix or '/'
    url = django_reverse(viewname, urlconf, args, kwargs, prefix, current_app)
    if prefixer:
        return prefixer.fix(url)
    else:
        return url


class Prefixer(object):

    def __init__(self, request):
        self.request = request
        split = self.split_path(request.path_info)
        self.locale, self.app, self.shortened_path = split

    def split_path(self, path_):
        """
        Split the requested path into (locale, app, remainder).

        locale and app will be empty strings if they're not found.
        """
        path = path_.lstrip('/')

        # Use partition instead of split since it always returns 3 parts.
        first, _, first_rest = path.partition('/')
        second, _, rest = first_rest.partition('/')

        if first.lower() in settings.LANGUAGES:
            if second in amo.APPS:
                return first, second, rest
            else:
                return first, '', first_rest
        elif first in amo.APPS:
            return '', first, first_rest
        else:
            if second in amo.APPS:
                return '', second, rest
            else:
                return '', '', path

    def get_language(self):
        """
        Return a locale code that we support on the site using the
        user's Accept Language header to determine which is best.  This
        mostly follows the RFCs but read bug 439568 for details.
        """
        if 'lang' in self.request.GET:
            lang = self.request.GET['lang'].lower()
            if lang in settings.LANGUAGE_URL_MAP:
                return settings.LANGUAGE_URL_MAP[lang]

        if self.request.META.get('HTTP_ACCEPT_LANGUAGE'):
            ranked_languages = parse_accept_lang_header(
                    self.request.META['HTTP_ACCEPT_LANGUAGE'])

            # Do we support or remap their locale directly?
            supported = [lang[0] for lang in ranked_languages if lang[0]
                        in settings.LANGUAGE_URL_MAP]

            # Do we support a less specific locale? (xx-YY -> xx)
            if not len(supported):
                for lang in ranked_languages:
                    supported = [x for x in settings.LANGUAGE_URL_MAP if
                                     lang[0].split('-', 1)[0] ==
                                     x.split('-', 1)[0]]
                    if supported:
                        break

            if len(supported):
                return settings.LANGUAGE_URL_MAP[supported[0]]

        return settings.LANGUAGE_CODE

    def fix(self, path):
        path = path.lstrip('/')
        url_parts = [self.request.META['SCRIPT_NAME']]

        if path.partition('/')[0] not in settings.SUPPORTED_NONLOCALES:
            locale = self.locale if self.locale else self.get_language()
            url_parts.append(locale)

        if path.partition('/')[0] not in settings.SUPPORTED_NONAPPS:
            app = self.app if self.app else settings.DEFAULT_APP
            url_parts.append(app)

        url_parts.append(path)

        return '/'.join(url_parts)


def get_outgoing_url(url):
    """
    Bounce a URL off an outgoing URL redirector, such as outgoing.mozilla.org.
    """
    if not settings.REDIRECT_URL:
        return url

    # no double-escaping
    if urlparse(url).netloc == urlparse(settings.REDIRECT_URL).netloc:
        return url

    hash = hashlib.sha1(settings.REDIRECT_SECRET_KEY + url).hexdigest()
    return '/'.join(
        [settings.REDIRECT_URL.rstrip('/'), hash, urllib.quote(url)])
