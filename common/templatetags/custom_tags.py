import re

from django import template
from django.core.urlresolvers import reverse, NoReverseMatch


register = template.Library()

cinema_list_regexp = re.compile('^/cinemas/[\d]{2}-[\d]{2}-[\d]{4}/$')


@register.simple_tag(takes_context=True)
def active(context, view_name):
    path = context['request'].path

    if view_name == 'cinema_list' and cinema_list_regexp.match(path):
        return 'active'

    try:
        return 'active' if (reverse(view_name) == path) else ''
    except NoReverseMatch:
        return ''
