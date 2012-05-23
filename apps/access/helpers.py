import jinja2
from jingo import register

import acl


@register.function
@jinja2.contextfunction
def check_ownership(context, object, require_owner=False,
                    require_author=False):
    return acl.check_ownership(context['request'], object,
                               require_owner=require_owner,
                               require_author=require_author)


@register.function
@jinja2.contextfunction
def action_allowed(context, app, action):
    return acl.action_allowed(context['request'], app, action)
