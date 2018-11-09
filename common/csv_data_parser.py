import csv

from django.db import IntegrityError
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from common.models import Dimension, GeneralContract, Cinema, Chain, City, CinemaHall, \
    ContactInformation
from users.models import User


class CsvParser:
    FORMATS = [
        '2D',
        '3D',
        '4D',
        'HFR',
        'HFR3D',
        '4K',
        'ATMOS',
        'D-BOX',
        '4DX 2D',
        '4DX 3D',
        'IMAX 2D',
        'IMAX 3D',
        'DVD',
        'HD',
        'DCP 2D',
        'DCP 3D',
    ]

    def __init__(self, csv_file_path):
        self.rows = []
        with open(csv_file_path, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)

            next(csv_reader)
            for row in csv_reader:
                self.rows.append(row)

    def upload_data_to_db(self):

        for row in self.rows:

            for ind, val in enumerate(row):
                row[ind] = val.strip().strip("'").strip('"')
                if row[ind] == '-':
                    row[ind] = ''

            try:
                number_of_gen_contract = row[1]
                city_name = row[4]
                chain_name = row[3]
                cinema_name = row[5]
                contractor_name = row[6]
                SBR_code = int(row[7]) if row[7] else ''
                raw_vat = row[8]
                cinema_hall_count = row[9]
                cinema_hall_name = row[10]
                cinema_hall_seats_count = row[11]
                formats = self._get_formats(row[12:28])
                raw_responsible_for_daily_reports_emails = row[28]
                raw_admin_phone_numbers = row[29]
                raw_access_to_reports_emails = row[30]
                raw_accountant_phone_numbers = row[31]

            except IndexError as e:
                import ipdb; ipdb.set_trace()

            else:
                if chain_name and chain_name != 'Independent':
                    chain = Chain.objects.get_or_create(name=chain_name)[0]
                else:
                    chain = None

                city = City.objects.get_or_create(name=city_name)[0] if city_name else None

                if city:
                    try:
                        if chain:
                            cinema = Cinema.objects.get(name=cinema_name, city=city, chain=chain)
                        else:
                            cinema = Cinema.objects.get(name=cinema_name, city=city)

                    except Cinema.DoesNotExist:

                        cinema = Cinema.objects.create(
                                name=cinema_name, city=city, chain=chain,
                                halls_count=cinema_hall_count if cinema_hall_count else 0,
                                vat=raw_vat == 'пдв')

                else:
                    cinema = None

                if cinema:
                    self.handle_users(raw_responsible_for_daily_reports_emails,
                                      raw_admin_phone_numbers, cinema, view_all_reports=False)

                    self.handle_users(raw_access_to_reports_emails, raw_accountant_phone_numbers,
                                      cinema, view_all_reports=True)

                if SBR_code and contractor_name and number_of_gen_contract and (cinema or chain):

                    if not GeneralContract.objects.filter(SBR_code=SBR_code).exists() and not \
                            GeneralContract.objects.filter(number=number_of_gen_contract).exists():

                        contract = GeneralContract(
                            SBR_code=SBR_code,
                            contractor_full_name=contractor_name,
                            number=number_of_gen_contract,
                            active_from=now().date()
                        )

                        if chain:
                            contract.chain = chain
                        if cinema:
                            contract.cinemas.add(cinema)

                        contract.save()

                if cinema:
                    try:
                        cinema_hall = CinemaHall.objects.create(
                            name=cinema_hall_name if cinema_hall_name else 'default name {}'.format(
                                get_random_string()),
                            seats_count=cinema_hall_seats_count if cinema_hall_seats_count else 0,
                            cinema=cinema,
                        )

                        for f in formats:
                            cinema_hall.dimensions.add(f)
                    except IntegrityError as e:
                        print('CinemaHall', e)

    def _get_formats(self, data):
        formats = []
        for index, value in enumerate(data):
            if value == '1':
                obj, created = Dimension.objects.get_or_create(name=self.FORMATS[index])
                formats.append(obj)
        return formats

    def handle_users(self, raw_emails, raw_phones, cinema, view_all_reports):
        emails_list = [e.strip().lower() for e in raw_emails.split(';')]
        emails_list = [e for e in emails_list if e]

        phones_list = [''.join(filter(str.isdigit, p)) for p in raw_phones.split(';')]
        phones_list = [p for p in phones_list if p]

        # create and bind user to cinema
        if emails_list:
            first_user_email = emails_list[0]
            user = User.objects.filter(email=first_user_email).first()
            if not user:
                user_params = dict(email=first_user_email, view_all_reports=view_all_reports)
                if len(emails_list) == 1:
                    user_params['phone_number'] = ';'.join(phones_list)
                user = User.objects.create(**user_params)
            if view_all_reports:
                cinema.access_to_reports.add(user)
            else:
                cinema.responsible_for_daily_reports.add(user)
            cinema.save()

        # create contact information
        contact_info_title = 'бухгалтер' if view_all_reports else 'администратор'
        try:
            if len(emails_list) == 1:
                ContactInformation.objects.create(
                    email=first_user_email,
                    phone_number=';'.join(phones_list),
                    title=contact_info_title,
                    cinema=cinema)
            else:
                for email in emails_list:
                    ContactInformation.objects.create(email=email, title=contact_info_title,
                                                      cinema=cinema)
                for phone_number in phones_list:
                    ContactInformation.objects.create(phone_number=phone_number,
                                                      title=contact_info_title, cinema=cinema)
        except IntegrityError:
            pass


def bind_user_to_chains():
    """This allows to bind users to chain if all chains cinemas has one user"""
    for c in Chain.objects.all():
        if len(set(c.cinemas.values_list('responsible_for_daily_reports', flat=True))) == 1:
            c.responsible_for_daily_reports.add(c.cinemas.first().responsible_for_daily_reports.first())

        if len(set(c.cinemas.values_list('access_to_reports', flat=True))) == 1:
            c.access_to_reports.add(c.cinemas.first().access_to_reports.first())

        c.save()


def normalize_contracts():
    """Normalize all GeneralContract with cinema is not None and chain is not None"""
    for gc in GeneralContract.objects.all():
        if gc.cinemas.exists() and gc.chain:
            gc.cinemas.update(chain_contract=gc)
            gc.cinemas.clear()
