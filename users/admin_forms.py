import csv
import io

from dal import autocomplete
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX
from django.core.validators import validate_email
from django.forms.utils import flatatt
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ugettext

from common.models import Chain, Cinema
from users.models import User


def validate_file_extension(value):
    if not value.name.endswith('.csv'):
        raise forms.ValidationError('Только csv файлы')


class UserTypeChoices:
    VIEW_REPORT = 'view_report'
    FULL = 'full'
    VIEW_ALL_REPORTS = 'view_all_reports'


USER_ACCESS_TYPE_CHOICES = {
        UserTypeChoices.VIEW_REPORT: 'Кинотеатр - Подача отчетов',
        UserTypeChoices.FULL: 'Кинотеатр - Полный доступ',
        UserTypeChoices.VIEW_ALL_REPORTS: 'Киномания - Просмотр'}


class FormLinkOnlyPasswordWidget(forms.Widget):
    def render(self, name, value, attrs):
        encoded = value
        final_attrs = self.build_attrs(attrs)

        if not encoded or encoded.startswith(UNUSABLE_PASSWORD_PREFIX):
            summary = mark_safe('<strong>%s</strong>' % ugettext('No password set.'))
        else:
            summary = ''
        return format_html('<div{}>{}</div>', flatatt(final_attrs), summary)


class CustomUserChangeForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget = FormLinkOnlyPasswordWidget()


class CustomUserCreationForm(forms.ModelForm):

    error_messages = {
        'password_mismatch': _('The two password fields didn\'t match.'),
    }

    ACCESS_TYPE_CHOICES = (('staff', 'Киномания-Админ'),) + tuple(
            ((k, v) for k, v in USER_ACCESS_TYPE_CHOICES.items()))

    username = forms.CharField(label='Имя пользователя', help_text='')

    access_type = forms.ChoiceField(label='Тип доступа', choices=ACCESS_TYPE_CHOICES,
                                    required=False)
    chain = forms.ModelMultipleChoiceField(label='Сеть', queryset=Chain.objects.all(), required=False,
                                           widget=autocomplete.ModelSelect2Multiple(url='chain_autocomplete'),
                                           help_text='Выбрать все кинотеатры сети')
    chain_cinema_filter = forms.ModelChoiceField(label='Фильтр по сети',
                                                 queryset=Chain.objects.all(),
                                                 required=False,
                                                 help_text='Отфильтровать кинотеатры по сети',
                                                 widget=autocomplete.ModelSelect2(
                                                     url='chain_autocomplete'))

    cinemas = forms.ModelMultipleChoiceField(
        label='Кинотеатры', queryset=Cinema.objects.all(), required=False,
        widget=autocomplete.ModelSelect2Multiple(url='cinema_autocomplete'))
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput,
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    class Meta:
        model = User
        fields = ('username', 'email')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        self.instance.username = self.cleaned_data.get('username')
        password_validation.validate_password(self.cleaned_data.get('password2'), self.instance)
        return password2

    def clean_cinemas(self):
        cinemas = self.cleaned_data['cinemas']
        chains = self.cleaned_data['chain']

        list_chains_ids = set(cinemas.values_list('chain_id', flat=True))

        if len(chains) > 0 and len(cinemas) > 0:
            raise forms.ValidationError("Выбирите или кинотеатр или сеть")

        if chains is not None:
            for chain in chains:
                if chain.id in list_chains_ids:
                    raise forms.ValidationError("Кинотеатр включен в сеть уже")

        if len(set(cinemas.values_list('chain_id', flat=True))) > 1:
            raise forms.ValidationError('Выберите кинотеатры из одной сети')

        return cinemas

    def save(self, commit=True):
        data = self.cleaned_data
        access_type = data['access_type']

        user = super().save(commit=False)
        user.set_password(data['password1'])
        if access_type == 'staff':
            user.is_superuser = True
            user.is_staff = True
        elif access_type == UserTypeChoices.VIEW_ALL_REPORTS:
            user.view_all_reports = True
        elif access_type == UserTypeChoices.FULL:
            user.is_staff = True

        user.save()

        User.objects.send_credentials_email(
            username=data['username'],
            email=data['email'],
            password=data['password1'],
            access_type=data['access_type'],
        )

        chains = data['chain']
        cinemas = data['cinemas']

        if chains:
            for chain in chains:
                if access_type == UserTypeChoices.VIEW_REPORT:
                    chain.responsible_for_daily_reports.add(user)
                    chain.save()

                    for cinema in chain.cinemas.all():
                        cinema.responsible_for_daily_reports.add(user)
                        cinema.save()

                elif access_type == UserTypeChoices.FULL:
                    chain.responsible_for_daily_reports.add(user)
                    chain.access_to_reports.add(user)
                    chain.save()

                    for cinema in chain.cinemas.all():
                        cinema.responsible_for_daily_reports.add(user)
                        cinema.access_to_reports.add(user)
                        cinema.save()

                chain.save()

        if cinemas:
            for cinema in cinemas:
                if access_type == UserTypeChoices.VIEW_REPORT:
                    cinema.responsible_for_daily_reports.add(user)
                elif access_type == UserTypeChoices.FULL:
                    cinema.responsible_for_daily_reports.add(user)
                    cinema.access_to_reports.add(user)

                cinema.save()

        return user


class ImportUsersForm(forms.Form):

    ACCESS_TYPE_CHOICES = USER_ACCESS_TYPE_CHOICES.keys()

    users_csv = forms.FileField(label='Импортировать пользователей из CSV файла',
                                validators=[validate_file_extension])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ADDED_DATA = {
            'emails': [],
            'chains': [],
            'cinemas': []}

    def clean_email(self, email):
        try:
            validate_email(email)
        except forms.ValidationError:
            raise forms.ValidationError('Невалидный имейл "{}"'.format(email))

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Пользователь с имейлом "{}" уже существует.'.format(
                email
            ))
        return email

    def clean_username(self, username):
        if len(username) > 150:
            raise forms.ValidationError('Слишком длинное имя пользователя "{}"'.format(username))

        return username

    def clean_access_type(self, access_type):
        if access_type not in self.ACCESS_TYPE_CHOICES:
            raise forms.ValidationError(
                '"{}" не валидный тип доступа к кинотеатру, валидные варианты это {}'.format(
                    access_type, ', '.join(self.ACCESS_TYPE_CHOICES)))

        return access_type

    def clean_chain_name(self, chain_name):
        chain = None
        if chain_name:
            chain_name = chain_name.strip()
            chain = Chain.objects.filter(name__iexact=chain_name).first()
            if not chain:
                raise forms.ValidationError(
                        'В базе данных нет сети с названием "{}"'.format(chain_name))
        return chain

    def clean_cinemas(self, cinemas, chain):
        clean_cinemas = []
        for cinema in cinemas.split(';'):
            if cinema:
                cinema_name, city_name = cinema.split(',')
                cinema_name = cinema_name.strip()
                city_name = city_name.strip()
                cinema = Cinema.objects.filter(
                    city__name__iexact=city_name, name__iexact=cinema_name, chain=chain).first()

                if not cinema:
                    error_msg = 'В базе данных нет кинотеатра с название "{}", городом "{}"'.format(
                        cinema_name, city_name)
                    if chain:
                        error_msg += ' в сети "{}"'.format(chain.name)
                    raise forms.ValidationError(error_msg)

                clean_cinemas.append(cinema)

        return clean_cinemas

    def clean_users_csv(self):
        """
        Row format: email:username:access_type:chain:city1, cinema_name1;city2, cinema_name2;
        """
        csv_file = self.cleaned_data['users_csv']

        cleaned_users = []

        for row in csv.DictReader(io.StringIO(csv_file.read().decode('utf-8')),
                                  delimiter=':', quotechar='|'):

            try:
                user_data = dict(
                    email=self.clean_email(row['email']),
                    username=self.clean_username(row['username']),
                    access_type=self.clean_access_type(row['access_type']),
                    chain=self.clean_chain_name(row['chain_name']))

                user_data['cinemas'] = self.clean_cinemas(row['cinemas'], user_data['chain'])

            except KeyError as err:
                raise forms.ValidationError('В файле нет столбца {}'.format(err))
            else:

                data = self.ADDED_DATA

                if user_data['email'] in data['emails']:
                    raise forms.ValidationError(
                        '"{}" этот имейл встречается несколько раз в файле'.format(
                                user_data['email']))
                else:
                    data['emails'].append(user_data['email'])

                if [user_data['chain'], user_data['access_type']] in data['chains']:
                    raise forms.ValidationError(
                        'Сеть "{}" c типом доступа "{}" уже есть в файле'.format(
                                user_data['chain'], user_data['access_type']))
                else:
                    data['chains'].append([user_data['chain'], user_data['access_type']])

                if user_data['cinemas']:
                    for cinema in user_data['cinemas']:
                        if [cinema, user_data['access_type']] in data['cinemas']:
                            raise forms.ValidationError(
                                'Кинотеатр "{}" с типом доступа "{}" уже есть в файле'.format(
                                    cinema, user_data['access_type']))
                        else:
                            data['cinemas'].append([cinema, user_data['access_type']])

                if user_data['access_type'] != UserTypeChoices.VIEW_ALL_REPORTS and not \
                        user_data['cinemas'] and not user_data['chain']:
                    raise forms.ValidationError(
                            'Введите сеть или кинотеатры для пользователя "{}"'.format(
                                    user_data['email']))

                cleaned_users.append(user_data)

        return cleaned_users
