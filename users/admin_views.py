from braces.views import FormValidMessageMixin
from braces.views import SuperuserRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from users.admin_forms import ImportUsersForm, UserTypeChoices
from users.models import User


class ImportUsersView(SuperuserRequiredMixin, FormValidMessageMixin, FormView):
    form_class = ImportUsersForm
    template_name = 'admin/import_users_view.html'
    success_url = reverse_lazy('admin:users_user_changelist')

    def form_valid(self, form):
        self.users_count = len(form.cleaned_data['users_csv'])

        for data in form.cleaned_data['users_csv']:
            access_type = data['access_type']
            chain = data['chain']
            cinemas = data['cinemas']
            password = User.make_random_password()

            user = User.objects.create_user(
                    email=data['email'],
                    username=data['username'],
                    password=password,
                    access_type=access_type,
                    view_all_reports=access_type == UserTypeChoices.VIEW_ALL_REPORTS)

            if chain and not cinemas:
                if access_type == UserTypeChoices.VIEW_REPORT:
                    chain.access_to_reports.add(user)
                else:
                    chain.responsible_for_daily_reports.add(user)
                    chain.access_to_reports.add(user)
                chain.save()
            else:
                for cinema in cinemas:
                    if access_type == UserTypeChoices.VIEW_REPORT:
                        cinema.access_to_reports.add(user)
                    else:
                        cinema.responsible_for_daily_reports.add(user)
                        cinema.access_to_reports.add(user)
                    cinema.save()

        return HttpResponseRedirect(self.get_success_url())

    def get_form_valid_message(self):
        # TODO find out why this is doesn't work
        return '{} пользователей успешно добавлено'.format(self.users_count)
