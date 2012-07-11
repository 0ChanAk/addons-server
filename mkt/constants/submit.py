from tower import ugettext_lazy as _


APP_STEPS = [
    ('terms', _('Developer Agreement')),
    ('manifest', _('App Manifest')),
    ('details', _('Details')),
    ('payments', _('Payments')),
    ('done', _('Finished!')),
]
APP_STEPS_TITLE = dict(APP_STEPS)

# Size requirements for uploaded app icons
APP_ICON_MIN_SIZE = (128, 128)

