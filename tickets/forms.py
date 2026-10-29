import re
from .phones import normalize_phone

from django import forms


class TicketForm(forms.Form):
    name = forms.CharField(max_length=100, strip=True)
    phone = forms.CharField(max_length=25, strip=True)
    agreement = forms.BooleanField()

    def clean_name(self):
        name = self.cleaned_data["name"]
        if len(name) < 2:
            raise forms.ValidationError("Укажите имя (не менее 2 символов).")
        return name

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        if not re.fullmatch(r"[+\d\s()\-]+", phone) or not normalize_phone(phone):
            raise forms.ValidationError("Укажите корректный номер телефона.")
        return phone
