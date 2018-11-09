import random
import string
from datetime import timedelta, time
from decimal import Decimal

import factory
from django.db import DataError
from django.db import IntegrityError
from django.utils import lorem_ipsum
from django.utils.timezone import now
from psycopg2._range import DateRange

from common.models import Chain, Cinema, City, CinemaHall, Film, Dimension, GeneralContract

ALL_CITY = City.objects.all()
ALL_CHAINS = Chain.objects.all()
ALL_CINEMAS = Cinema.objects.all()
ALL_FILMS = Film.objects.all()
ALL_CINEMA_HALLS = CinemaHall.objects.all()
ALL_DIMENSIONS = Dimension.objects.all()
ALL_CONTRACTS = GeneralContract.objects.all()


def random_bool():
    return bool(round(random.random()))


def get_random_date(future=False):
    dispersion = 100
    current_date = now().date()
    days_count = random.randint(0, dispersion)

    if future:
        return current_date + timedelta(days=days_count + dispersion + 1)

    if not random_bool():
        return current_date - timedelta(days=days_count)

    return current_date + timedelta(days=days_count)


def get_random_time():
    return time(random.randint(0, 23), random.randint(0, 59))


class StubbornFactory(factory.DjangoModelFactory):

    @classmethod
    def create_batch(cls, size, **kwargs):
        result = []
        for _ in range(size):
            result.append(cls.build(**kwargs))
        try:
            return cls._meta.model.objects.bulk_create(result, batch_size=1000)
        except (IntegrityError, DataError) as e:
            print('ERROR:', cls._meta.model, e)
            return []


class ChainFactory(StubbornFactory):
    class Meta:
        model = Chain

    @factory.lazy_attribute
    def name(self):
        return lorem_ipsum.words(3, False)


class CinemaFactory(StubbornFactory):
    class Meta:
        model = Cinema

    @factory.lazy_attribute
    def name(self):
        return lorem_ipsum.words(2, False)

    @factory.lazy_attribute
    def chain(self):
        if random_bool():
            return random.choice(ALL_CHAINS)

    @factory.lazy_attribute
    def city(self):
        return random.choice(ALL_CITY)

    @factory.lazy_attribute
    def vat(self):
        return random_bool()


class CinemaHallFactory(StubbornFactory):

    class Meta:
        model = CinemaHall

    @factory.lazy_attribute
    def name(self):
        return '{}-{}'.format(
            self.cinema.name,
            ''.join([random.choice(string.ascii_letters) for _ in range(4)]))

    @factory.lazy_attribute
    def cinema(self):
        return random.choice(ALL_CINEMAS)

    @factory.lazy_attribute
    def seats_count(self):
        return random.randint(1, 200)


class FilmFactory(StubbornFactory):

    class Meta:
        model = Film

    @factory.lazy_attribute
    def name(self):
        return lorem_ipsum.words(4, False)

    @factory.lazy_attribute
    def code(self):
        return ''.join([random.choice(string.ascii_letters) for _ in range(20)])

    @factory.lazy_attribute
    def release_date(self):
        return get_random_date()


class SessionFactory(StubbornFactory):

    class Meta:
        model = 'common.Session'

    @factory.lazy_attribute
    def date(self):
        return get_random_date()

    @factory.lazy_attribute
    def time(self):
        return get_random_time()

    @factory.lazy_attribute
    def viewers_count(self):
        return random.randint(0, 200)

    @factory.lazy_attribute
    def cinema_hall(self):
        return random.choice(ALL_CINEMA_HALLS)

    @factory.lazy_attribute
    def film(self):
        return random.choice(ALL_FILMS)

    @factory.lazy_attribute
    def min_price(self):
        return Decimal(random.random() * 100)

    @factory.lazy_attribute
    def max_price(self):
        return self.min_price + 100

    @factory.lazy_attribute
    def invitations_count(self):
        return random.randint(0, 50)

    @factory.lazy_attribute
    def gross_yield(self):
        return self.min_price * self.viewers_count

    @factory.lazy_attribute
    def vat(self):
        return random_bool()

    @factory.lazy_attribute
    def dimension(self):
        return random.choice(ALL_DIMENSIONS)


class GeneralContractFactory(StubbornFactory):

    class Meta:
        model = 'common.GeneralContract'

    @factory.lazy_attribute
    def contractor_full_name(self):
        return lorem_ipsum.words(3, False)

    @factory.lazy_attribute
    def SBR_code(self):
        return random.randint(1, 999999999)

    @factory.lazy_attribute
    def number(self):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(30))

    @factory.lazy_attribute
    def active_from(self):
        return get_random_date()

    @factory.lazy_attribute
    def chain(self):
        if random_bool():
            return random.choice(ALL_CHAINS)

    @factory.lazy_attribute
    def cinema(self):
        if not self.chain:
            return random.choice(ALL_CINEMAS)


class AdditionalAgreementFactory(StubbornFactory):

    class Meta:
        model = 'common.AdditionalAgreement'

    @factory.lazy_attribute
    def cinema(self):
        return random.choice(ALL_CINEMAS)

    @factory.lazy_attribute
    def contract(self):
        return random.choice(ALL_CONTRACTS)

    @factory.lazy_attribute
    def film(self):
        return random.choice(ALL_FILMS)

    @factory.lazy_attribute
    def active_date_range(self):
        return DateRange(get_random_date(), get_random_date(future=True))

    @factory.lazy_attribute
    def dimension(self):
        return random.choice(ALL_DIMENSIONS)

    @factory.lazy_attribute
    def vat(self):
        return random_bool()
