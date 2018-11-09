from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from django import forms


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(label='Действующий пароль', widget=forms.PasswordInput)
    new_password1 = forms.CharField(label='Новый пароль', widget=forms.PasswordInput)
    new_password2 = forms.CharField(label='Новый пароль (ещё раз)', widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.form_show_errors = True

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-4'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(

            'current_password',
            'new_password1',
            'new_password2',
            Submit('change_password', 'Сменить пароль', css_class='btn-primary btn-primary')
        )

    def clean_current_password(self):
        password = self.cleaned_data.get('current_password')
        if not self.user.check_password(password):
            raise forms.ValidationError('Неверный пароль')
        return password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError('Пароли не совпадают')
        return password2

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data['new_password1'])
        if commit:
            self.user.save()
        return self.user
