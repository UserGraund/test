from django.core.management.base import BaseCommand

from common.factories import FilmFactory, ChainFactory, CinemaFactory, CinemaHallFactory, \
    SessionFactory, GeneralContractFactory, AdditionalAgreementFactory
from common.models import Chain, Cinema, CinemaHall, Film, Session, Dimension, \
    AdditionalAgreement, GeneralContract
from kinomania.utils import query_yes_no, add_dimension


class Command(BaseCommand):
    chunk_size = 1000

    OBJECTS_AMOUNTS = [
        (ChainFactory, 2),
        (CinemaFactory, 20),
        (CinemaHallFactory, 80),
        (FilmFactory, 20),
        (SessionFactory, 200),
        (GeneralContractFactory, 10),
        (AdditionalAgreementFactory, 60),
    ]

    def handle(self, *args, **options):

        if query_yes_no('[DANGER!] Do you want to remove current data from data base?',
                        default='no'):

            Chain.objects.all().delete()
            Cinema.objects.all().delete()
            CinemaHall.objects.all().delete()
            Film.objects.all().delete()
            Session.objects.all().delete()
            GeneralContract.objects.all().delete()
            AdditionalAgreement.objects.all().delete()

        if not Dimension.objects.exists():
            for name in ['2d', '3d', '4d', '4dx', '5d']:
                Dimension.objects.create(name=name)

        for factory, amount in self.OBJECTS_AMOUNTS:
            objects = getattr(factory, 'create_batch')(amount)
            if factory._meta.model.__name__ in ['CinemaHall', 'Film']:
                add_dimension(objects)
            print(factory, 'created {} objects'.format(len(objects)))

