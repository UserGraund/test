import json
import os
import random
import sys

import math
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils.timezone import now


MONTHS = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь',
          'Октябрь', 'Ноябрь', 'Декабрь']


def is_weekend(date):
    holidays_dates = [  # [day, month]
        [1, 1],
        [7, 1],
        [8, 3],
        [1, 5],
        [2, 5],
        [9, 5],
        [28, 6],
        [24, 8],
        [14, 10],
    ]

    return (date.weekday() > 4) or ([date.day, date.month] in holidays_dates)


def get_previous_dates(date):
    """Returns required report dates.
    For example:
        if date is Monday - returns dates of Friday, Saturday and Sunday;
        if date is Friday - returns date of Thursday;
        if date is March 9 - returns March 7 and March 8
    """

    previous_dates = []
    delta_days = 1
    while True:
        previous_date = date - timedelta(days=delta_days)
        previous_dates.append(previous_date)
        if not is_weekend(previous_date):
            return previous_dates
        delta_days += 1


class StrEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def validate_xls_extension(value):
    ext = os.path.splitext(value.name)[1]
    valid_formats = ['.xls']
    if ext.lower() not in valid_formats:
        raise ValidationError('Only {} files.'.format(', '.join(valid_formats)))


def query_yes_no(question, default='yes'):
    """
    Ask a yes/no question via raw_input() and return their answer.

    'question' is a string that is presented to the user.
    'default' is the presumed answer if the user just hits <Enter>.
        It must be 'yes' (the default), 'no' or None (meaning
        an answer is required of the user).

    The 'answer' return value is True for 'yes' or False for 'no'.
    """
    valid = {'yes': True, 'y': True, 'ye': True,
             'no': False, 'n': False}
    if default is None:
        prompt = ' [y/n] '
    elif default == 'yes':
        prompt = ' [Y/n] '
    elif default == 'no':
        prompt = ' [y/N] '
    else:
        raise ValueError('invalid default answer: {}'.format(default))

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]

        sys.stdout.write('Please respond with \'yes\' or \'no\' (or \'y\' or \'n\').\n')


@transaction.atomic
def add_dimension(objects_list):
    from common.models import Dimension

    dimensions = list(Dimension.objects.all())
    for obj in objects_list:
        obj.dimensions.add(random.choice(dimensions))
    print('Added {} dimensions to {}'.format(len(objects_list),
                                             objects_list[0].__class__.__name__))


def chunks(qs, chunk_size=10000):
    chunks_count = math.ceil(qs.count() / chunk_size)
    for i in range(chunks_count):
        offset, limit = i * chunk_size, (i + 1) * chunk_size
        yield qs[offset:limit]


def build_full_url(url):
    site = Site.objects.get_current()
    # TODO use logger if site doesn't exists
    return 'http://{}{}'.format(site.domain if site else 'localhost', url)


def get_create_session_ulr(cinema, date):
    return reverse('create_session', kwargs={
            'pk': cinema.pk,
            'date': date.strftime(settings.DATE_URL_INPUT_FORMAT)})


def put_forms_errors_to_messages(request, form, only_first=False):
    for field_name, error_msg in form.errors.items():
        if field_name == '__all__':
            error_msg = error_msg[0]
        else:
            field = form.fields[field_name]
            error_msg = '{}: {}'.format(field.label if field.label else field_name,
                                        error_msg[0].lower())
        messages.error(request, error_msg)
        if only_first:
            break


def get_initial_year_and_month():
    today = now().date()
    if today.month == 1:
        return {'year': today.year - 1, 'month': 12}

    return {'year': today.year, 'month': today.month - 1}
