import csv
import os
import uuid
from decimal import Decimal
from html import escape
from io import BytesIO
from wsgiref.util import FileWrapper

import dbf
import xlsxwriter
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.template import Context
from django.template.loader import get_template
from django.utils.formats import date_format
from xhtml2pdf import pisa

from common.forms import ExportReportForm
from common.tables import ReportTable
from kinomania.utils import chunks


class Echo:
    def write(self, value):
        return value


class MonthlyReportPdfExporter:

    template_name = 'dashboard/monthly_report_pdf.html'

    def __init__(self, queryset, first_session, summary_data, full_static_path):
        self.queryset = queryset
        self.first_session = first_session
        self.full_static_path = full_static_path
        self.summary_data = summary_data

    def export_to_response(self):
        template = get_template(self.template_name)
        context_dict = {
            'dates_list': self.queryset,
            'first_session': self.first_session,
            'full_static_path': self.full_static_path,
            'summary_data': self.summary_data
        }
        context = Context(context_dict)
        html = template.render(context)

        result = BytesIO()
        encoding = 'utf8'
        pdf = pisa.pisaDocument(BytesIO(html.encode(encoding)), result, encoding,
                                show_error_as_pdf=True)
        if not pdf.err:
            return HttpResponse(result.getvalue(), content_type='application/pdf')

        return HttpResponse('We had some errors<pre>%s</pre>' % escape(html))


class MonthlyReportXlsExporter:

    def __init__(self, queryset, first_session, summary_data):
        self.queryset = queryset
        self.first_session = first_session
        self.summary_data = summary_data

        self.file_name = '{film} ({month} {year}).xlsx'.format(
                film=self.first_session.film.name,
                month=self.first_session.date.strftime('%B'),
                year=self.first_session.date.year)

        files_dir = 'monthly_reports/'
        if not os.path.exists(files_dir):
            os.makedirs(files_dir)
        self.file_path = files_dir + self.file_name
        self.workbook = xlsxwriter.Workbook(self.file_path)
        self.worksheet = self.workbook.add_worksheet()

        self.styles = {
            'bold': self.workbook.add_format({'bold': True}),
            't_head': self.workbook.add_format({'bold': True, 'align': 'center', 'border': True}),
            't_body': self.workbook.add_format({'align': 'center', 'border': True})
        }

    def export_to_response(self):
        self.write_data_to_file()

        file_path = os.path.join(settings.BASE_DIR, self.file_path)
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(self.file_name)
            return response

    def write_data_to_file(self):
        worksheet = self.worksheet
        styles = self.styles

        for letter in 'BC':
            worksheet.set_column(letter + ':' + letter, 30)
        for letter in 'DEFG':
            worksheet.set_column(letter + ':' + letter, 20)

        worksheet.merge_range('D1:E1', 'РОЗРАХУНКОВИЙ БЛАНК', styles['bold'])

        for row_number, row_data in enumerate(self.prepare_file_header_data(), 1):
            for col_number, cell in enumerate(row_data, 1):
                worksheet.write(
                        row_number, col_number, cell, styles['bold'] if col_number == 1 else None)

        for col_number, cell in enumerate(['Дата', 'Кількість сеансів', 'Глядачі', 'Валовий збір',
                                           'Валовий збір без ПДВ', 'РОЯЛТІ'], 1):
            worksheet.write(10, col_number, cell, styles['t_head'])

        style = styles['t_body']
        for row_number, date_data in enumerate(self.queryset):
            worksheet.write(row_number + 11, 1, date_format(date_data['date']), style)
            worksheet.write(row_number + 11, 2, date_data['session_count'], style)
            worksheet.write(row_number + 11, 3, date_data['sum_viewers_count'], style)
            worksheet.write(row_number + 11, 4, date_data['sum_gross_yield'], style)
            worksheet.write(row_number + 11, 5, date_data['sum_gross_yield_without_vat'], style)
            worksheet.write(row_number + 11, 6, "{:.2f}".format(date_data['income']), style)

        sum_data = self.summary_data
        style = styles['t_head']
        worksheet.write(row_number + 12, 1, 'Всього:', style)
        worksheet.write(row_number + 12, 2, sum_data['total_session_count'], style)
        worksheet.write(row_number + 12, 3, sum_data['total_sum_viewers_count'], style)
        worksheet.write(row_number + 12, 4, intcomma(sum_data['total_sum_gross_yield']), style)
        worksheet.write(row_number + 12, 5, intcomma(sum_data['total_sum_gross_yield_without_vat']),
                        style)
        worksheet.write(row_number + 12, 6, "{:,.2f}".format(sum_data['total_income']), style)

        self.workbook.close()

    def prepare_file_header_data(self):
        if not self.first_session:
            return []

        header = [
            ['Назва фільму:', self.first_session.film.name],
            ['Формат фільмокопії:', self.first_session.dimension.name],
            ['Кінотеатр:', '"{}"'.format(self.first_session.cinema_hall.cinema.name), '',
             'Місто:', self.first_session.cinema_hall.cinema.city.name]
        ]

        additional_agreement = self.first_session.additional_agreement
        if additional_agreement:
            contract = additional_agreement.contract
            header.extend([
                ['Генеральний договір:', contract.number, '', 'від',
                 date_format(contract.active_from)],
                ['Додаток дійсний:',
                 'з', date_format(additional_agreement.active_date_range.lower),
                 'по', date_format(additional_agreement.active_date_range.upper)],
                ['Демонстратор (контрагент):', additional_agreement.contract.contractor_full_name]])

        header.append(['Дистриб\'ютор', 'ТОВ "Кіноманія"'])
        return header


class SessionCsvExporter:

    def __init__(self, export_form, queryset):
        self.export_params = export_form.cleaned_data
        self.export_format = self.export_params['export_format']
        self.form = export_form
        self.queryset = queryset
        self.flat_columns = {c[0]: c[1] for c in self.form.fields['flat_columns'].choices}
        self.grouped_columns = {c[0]: c[1] for c in self.form.fields['grouped_columns'].choices}

    def csv_to_response(self, queryset, columns_names, group_by):
        pseudo_buffer = Echo()
        dict_writer = csv.DictWriter(pseudo_buffer, columns_names)
        simple_writer = csv.writer(pseudo_buffer)

        """Note: content_type with charset "Windows-1251" will raise UnicodeEncodeError"""
        response = StreamingHttpResponse(
                self.write_csv(group_by, queryset, columns_names, simple_writer, dict_writer),
                content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sessions.csv"'
        return response

    def prepare_session_row(self, session, columns_names, group_by):

        session_row = {}
        if group_by:
            for column_name in columns_names:
                if column_name == 'period':
                        value = ReportTable.render_period(session, is_export=True)
                elif hasattr(ReportTable, 'render_' + column_name):
                    value = getattr(ReportTable, 'render_' + column_name)(session)
                else:
                    value = session[column_name]

                if self.export_format == 'csv':
                    session_row[column_name] = value
                else:
                    session_row[ExportReportForm.GROUPED_EXPORT_COLUMNS[column_name][0]] = value
        else:
            agreement = session.additional_agreement
            cinema = session.cinema_hall.cinema
            chain = cinema.chain

            if 'id' in columns_names:
                session_row['id'] = session.id
            if 'hall' in columns_names:
                session_row['hall'] = session.cinema_hall.name
            if 'cinema' in columns_names:
                session_row['cinema'] = cinema.name
            if 'chain' in columns_names:
                session_row['chain'] = chain.name if chain else ''
            if 'film' in columns_names:
                session_row['film'] = session.film.name
            if 'film_code' in columns_names:
                session_row['film_code'] = session.film.code
            if 'date' in columns_names:
                session_row['date'] = session.date
            if 'time' in columns_names:
                session_row['time'] = '{}'.format(session.time)
            if 'min_price' in columns_names:
                session_row['min_price'] = session.min_price
            if 'max_price' in columns_names:
                session_row['max_price'] = session.max_price
            if 'viewers' in columns_names:
                session_row['viewers'] = session.viewers_count
            if 'invitation' in columns_names:
                session_row['invitation'] = session.invitations_count
            if 'yield' in columns_names:
                session_row['yield'] = session.gross_yield
            if 'income' in columns_names:
                session_row['income'] = session.gross_yield_without_vat * \
                                       Decimal(settings.KINOMANIA_INCOME_FEE)
            if 'dimension' in columns_names:
                session_row['dimension'] = session.dimension.name
            if 'vat' in columns_names:
                session_row['vat'] = session.vat
            if 'contr_num' in columns_names:
                session_row['contr_num'] = agreement.contract.number if agreement else ''
            if 'contr_code' in columns_names:
                session_row['contr_code'] = agreement.contract.SBR_code if agreement else dbf.Null
            if 'agr_date_s' in columns_names:
                session_row['agr_date_s'] = agreement.active_date_range.lower if agreement else \
                    dbf.Date()
            if 'agr_date_e' in columns_names:
                session_row['agr_date_e'] = agreement.active_date_range.upper if agreement else \
                    dbf.Date()
            if 'language' in columns_names:
                session_row['language'] = 'original' if session.is_original_language else \
                    'ukrainian'
            if 'created' in columns_names:
                session_row['created'] = session.created
            if 'modified' in columns_names:
                session_row['modified'] = session.modified

        return session_row

    def write_csv(self, group_by, queryset, columns_names, simple_writer, dict_writer):
        yield simple_writer.writerow(['sep=,'])  # for correct opening in Excel

        if group_by:
            table_header = {col_name: self.grouped_columns[col_name] for
                            col_name in columns_names}
        else:
            table_header = {col_name: self.flat_columns[col_name] for
                            col_name in columns_names}

        yield dict_writer.writerow(table_header)

        for chunk in chunks(queryset, 50000):
            for session in chunk:
                yield dict_writer.writerow(
                        self.prepare_session_row(session, columns_names, group_by))

    def export_to_response(self):
        export_params = self.export_params
        export_group_by = export_params.get('export_group_by')
        grouped_columns = export_params['grouped_columns']
        flat_columns = export_params['flat_columns']

        columns_names = grouped_columns if export_group_by else flat_columns

        group_by = export_params.get('export_group_by')

        queryset = self.queryset
        if not group_by:
            queryset = queryset.select_related(
                'cinema_hall',
                'cinema_hall__cinema',
                'cinema_hall__cinema__chain',
                'additional_agreement',
                'additional_agreement__contract',
                'dimension',
                'film')

        if self.export_format == 'csv':
            return self.csv_to_response(queryset, columns_names, group_by)
        else:
            return self.dbf_to_response(queryset, columns_names, group_by)

    def create_dbf_table(self, columns_names, group_by):
        if group_by:
            table_columns = ['{} {}'.format(col[0], col[1])
                             for name, col in ExportReportForm.GROUPED_EXPORT_COLUMNS.items()
                             if name in columns_names]
        else:
            table_columns = ['{} {}'.format(col[0], col[2])
                             for col in ExportReportForm.FLAT_EXPORT_COLUMNS
                             if col[0] in columns_names]
        table_schema = '; '.join(table_columns)

        table_name = 'sessions_table-{}'.format(uuid.uuid4().urn.rsplit(':', 1)[1])

        return dbf.Table(
            table_name,
            table_schema,
            codepage='cp1251'), table_name

    def dbf_to_response(self, queryset, columns_names, group_by):
        sessions_table, table_name = self.create_dbf_table(columns_names, group_by)
        sessions_table.open()
        for chunk in chunks(queryset, 50000):
            for session in chunk:
                sessions_table.append(self.prepare_session_row(session, columns_names, group_by))

        file_name = table_name + '.dbf'

        wrapper = FileWrapper(open(file_name, 'rb'))
        response = HttpResponse(wrapper, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename=sessions.dbf'
        response['Content-Length'] = os.path.getsize(file_name)
        os.remove(file_name)
        return response
