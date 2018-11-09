from django import forms


class MultipleFileInput(forms.FileInput):

    def render(self, name, value, attrs=None):
        attrs['multiple'] = 'multiple'
        return super().render(name, value, attrs)

    def value_from_datadict(self, data, files, name):

        if hasattr(files, 'getlist'):
            return files.getlist(name)
        else:
            value = files.get(name)
            if isinstance(value, list):
                return value
            else:
                return [value]


class MultipleFileField(forms.FileField):

    widget = MultipleFileInput

    def to_python(self, data):

        ret = []
        data = data or []
        for item in data:
            i = super().to_python(item)
            if i:
                ret.append(i)
        return ret
