import copy
import json
import re
from datetime import datetime
from decimal import Decimal

import xlrd
from dateutil import parser
from django.core.exceptions import MultipleObjectsReturned
from django.db import IntegrityError
from prettytable import PrettyTable
from xlrd import XLRDError

from common.models import Session, CinemaHall, Film, Cinema, Chain, Dimension, \
    FinishedCinemaReportDate
from kinomania.utils import StrEncoder


class XlsReportParser:

    BLOCK_BEGIN_TEXT = 'Звіт про результати демонстрування'
    BLOCK_END_TEXT = 'Всього за день'
    SESSION_END_TEXT = 'Всього за Сеанс'
    CHAIN_NAME = 'Multiplex'

    def __init__(self, path_to_xls, xls_report, city=None):
        self.xls_report = xls_report
        self.all_sessions_data = []
        self.errors = set()
        self.city = city
        try:
            rb = xlrd.open_workbook(path_to_xls, formatting_info=True)
        except XLRDError:
            self.is_file_invalid = True
        else:
            self.is_file_invalid = False
            self.sheet = rb.sheet_by_index(0)

    def parse_xls_file(self):
        """First stage"""
        save_rows = None
        film_block = []
        for row_num in range(self.sheet.nrows):
            row_values = [str(val).strip() for val in self.sheet.row_values(row_num)]
            if any(row_values):
                for col_num, cell_value in enumerate(row_values):
                    if cell_value == self.BLOCK_BEGIN_TEXT:
                        save_rows = True
                    elif cell_value == self.BLOCK_END_TEXT:
                        save_rows = False
                        self.handle_film_block(film_block)

                        film_block = []

                if save_rows:
                    film_block.append(row_values)

        return self.all_sessions_data

    @staticmethod
    def print_block(block):
        p = PrettyTable()
        for row in block:
            p.add_row(row)

        print(p.get_string())
        print('-' * 20)

    @staticmethod
    def print_dict(_dict):
        for k, v in _dict.items():
            print('{}: {}'.format(k, v))
        print('-' * 20)

    def handle_film_block(self, block):
        """Second stage"""
        session_data = dict(raw_date=block[1][8], cinema_name=block[1][1].split(',')[0])

        session_data['film_name'], session_data['dimension_name'] = block[2][1].rsplit(' ', 1)

        data_rows = False
        reg = re.compile('^\d{2}.\d{2}.\d{4}.*$')
        for row in block:
            if reg.match(row[1]):
                data_rows = True
                date_and_time_and_hall = row[1]
                session_data['prices'] = []

                raw_time = re.findall('\d{1,2}:\d{2}[:\d{2}]*', date_and_time_and_hall)
                session_data['raw_time'] = raw_time[0] if raw_time else ''

                session_data['hall_name'] = date_and_time_and_hall.rsplit(
                        ',', 1)[1].replace('Зал ', '').strip()

                continue

            elif row[1] == self.SESSION_END_TEXT:
                session_data['viewers_count'] = row[3]
                session_data['invitations_count'] = row[5]

                session_data['gross_yield'] = row[8]
                self.all_sessions_data.append(copy.deepcopy(session_data))
                data_rows = False

            if data_rows:
                session_data['prices'].append(row[4])

    def create_sessions(self, all_sessions_data, chain):
        """Third stage"""

        cinema_name = all_sessions_data[0]['cinema_name']

        cinema_params = dict(name__iexact=cinema_name, chain=chain)

        if self.city:
            cinema_params['city'] = self.city

        try:
            cinema = Cinema.objects.get(**cinema_params)
        except Cinema.DoesNotExist:
            error_text = 'В базі даних немає кінотеатру з такою  назвою: "{}"'.format(
                    cinema_params['name__iexact'])
            if self.city:
                error_text += ', в місті "{}"'.format(self.city.name)

            self.errors.add(error_text)
            return

        except MultipleObjectsReturned:
            self.errors.add('В базі даних  декілька кінотеатрів з такою  назвою: "{}". '
                            'Попробуйте вказати місто перед загрузкою файлу.'.format(
                                    cinema_params['name__iexact']))
            return

        for session_data in all_sessions_data:

            hall_name = session_data.get('hall_name', '')
            cinema_hall = CinemaHall.objects.filter(cinema=cinema, name__iexact=hall_name).first()
            if not cinema_hall:
                if '№' in hall_name:
                    hall_name = hall_name.replace('№', '')
                else:
                    hall_name = '№' + hall_name
                cinema_hall = CinemaHall.objects.filter(
                        cinema=cinema, name__iexact=hall_name).first()
                if not cinema_hall:
                    self.errors.add('У кинотеатра "{}" нет зала с названием "{}"'.format(
                            cinema.name, hall_name))
                    continue

            try:
                dimension = Dimension.objects.get(name__iexact=session_data['dimension_name'])
            except Dimension.DoesNotExist:
                self.errors.add('В базе данных нет формата с названием "{}"'.format(
                        session_data['dimension_name']))
                continue

            session_date = datetime.strptime(session_data['raw_date'], '%d.%m.%Y').date()

            params = dict(
                dimension=dimension,
                cinema_hall=cinema_hall,
                date=session_date,
                time=parser.parse(session_data['raw_time']).time(),
            )

            if Session.objects.filter(**params).exists():
                self.errors.add('Сеанс {} уже существует'.format(
                      json.dumps(params, cls=StrEncoder)))
                continue

            try:
                film = Film.objects.get(
                    name__iexact=session_data['film_name'])
                is_original_language = False
            except (Film.DoesNotExist, MultipleObjectsReturned):
                film = Film.objects.filter(
                    name_original__iexact=session_data['film_name']).first()
                is_original_language = True

            if not film:
                self.errors.add('В базе данных нет фильма с названием "{}"'.format(
                        session_data['film_name']))
                continue
            else:
                params['film'] = film

            all_prices = [Decimal(price) for price in session_data['prices']]
            params['min_price'] = min(all_prices)
            params['max_price'] = max(all_prices)
            params['viewers_count'] = int(float(session_data['viewers_count']))
            params['invitations_count'] = int(float(session_data['invitations_count']))
            params['gross_yield'] = Decimal(session_data['gross_yield'])
            params['is_daily_report_finished'] = True
            params['xls_raw_data'] = session_data
            params['xls_session_report'] = self.xls_report
            params['is_original_language'] = is_original_language

            Session.objects.create(**params)

            try:
                FinishedCinemaReportDate.objects.create(date=session_date, cinema=cinema)
            except IntegrityError:
                pass

    def handle(self):

        if self.is_file_invalid:
            self.xls_report.errors = ['Файл {} повреждён.'.format(self.xls_report.xls_filename)]
            self.xls_report.save(parse_file=False)

        else:
            chain = Chain.objects.filter(name__iexact=self.CHAIN_NAME).first()
            if not chain:
                self.errors.add('В базе данных нет сети с названием "{}"'.format(self.CHAIN_NAME))
            else:
                self.create_sessions(all_sessions_data=self.parse_xls_file(), chain=chain)

            if self.errors:
                self.xls_report.errors = list(self.errors)
                self.xls_report.save(parse_file=False)
