from braces.views import FormValidMessageMixin
from braces.views import LoginRequiredMixin
from braces.views import UserFormKwargsMixin
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse_lazy
from django.views.generic import FormView

from users.forms import ChangePasswordForm


class ChangePasswordView(FormValidMessageMixin, UserFormKwargsMixin, LoginRequiredMixin, FormView):
    form_class = ChangePasswordForm
    form_valid_message = 'Новый пароль сохранён'
    success_url = reverse_lazy('change_password')
    template_name = 'dashboard/change_password.html'

    def form_valid(self, form):
        form.save()
        update_session_auth_hash(self.request, form.user)
        return super().form_valid(form)
