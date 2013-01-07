import re

from tower import ugettext_lazy as _

from versions.compare import version_int as vint


# These are the minimum versions required for `navigator.mozApps` support.
APP_PLATFORMS = [
    # Firefox for Desktop.
    (
        [
            re.compile('Firefox/([\d.]+)')
        ],
        vint('16.0')
    ),
    # Firefox for Android.
    (
        [
            re.compile('Fennec/([\d.]+)'),
            re.compile('Android; Mobile; rv:([\d.]+)'),
            re.compile('Mobile; rv:([\d.]+)')
        ],
        vint('17.0')
    )
]

FREE_PLATFORMS = (
    ('free-firefoxos', _('Firefox OS')),
    ('free-desktop', _('Firefox')),
    ('free-android-mobile', _('Firefox Mobile')),
    ('free-android-tablet', _('Firefox Tablet')),
)

PAID_PLATFORMS = (
    ('paid-firefoxos', _('Firefox OS')),
)

# Extra information about those values for display in the page.
DEVICE_LOOKUP = {
    'free-firefoxos': _('Fully open mobile ecosystem'),
    'free-desktop': _('Windows, Mac and Linux'),
    'free-android-mobile': _('Android smartphones'),
    'free-android-tablet': _('Android tablets'),
    'paid-firefoxos': _('Fully open mobile ecosystem'),
}
