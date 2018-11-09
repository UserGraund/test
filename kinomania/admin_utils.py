from django.urls import reverse


class ChangeLinkMixin:

    change_link_description = 'Изменить'

    def change_link(self, obj):
        url = reverse('admin:%s_%s_change' % (self.opts.app_label,
                                              self.opts.model_name),
                      args=(obj.pk,))
        return '<a href="{}">{}</a>'.format(url, self.change_link_description)

    change_link.allow_tags = True
    change_link.short_description = 'Action'

    def get_list_display(self, request):
        return ('change_link', ) + super().get_list_display(request)
