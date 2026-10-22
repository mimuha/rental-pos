import os
import re
import uuid
from decimal import Decimal, InvalidOperation

import requests
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import VehiclePhoto, Rental, MAX_PHOTOS_PER_VEHICLE, MAX_FILE_SIZE

MONEY_FIELD_NAMES = {
    'daily_rate',
    'deposit_amount',
    'discount_amount',
    'additional_fee',
    'total_cost',
    'amount',
}


def normalize_rupiah_value(value):
    if value is None:
        return value

    text = str(value).strip()
    if not text:
        return text

    text = text.replace('\u00a0', '').replace('\u202f', '').replace(' ', '')
    text = re.sub(r'(?i)^rp\.?\s*', '', text)

    if ',' in text:
        if '.' in text:
            text = text.replace('.', '')
        text = text.replace(',', '.')
    elif '.' in text and re.fullmatch(r'\d{1,3}(?:\.\d{3})+', text):
        text = text.replace('.', '')

    return text


class RupiahWidget(forms.TextInput):
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'vTextField rupiah-input',
            'inputmode': 'decimal',
            'autocomplete': 'off',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def format_value(self, value):
        if value is None or value == '':
            return ''

        try:
            source = value if isinstance(value, Decimal) else normalize_rupiah_value(value)
            number = Decimal(source)
        except (InvalidOperation, TypeError, ValueError):
            return super().format_value(value)

        formatted = f'{number.quantize(Decimal("0.01")):,.2f}'
        integer, _, decimal = formatted.partition('.')
        integer = integer.replace(',', '.')
        if decimal == '00':
            return integer
        return f'{integer},{decimal}'


class RupiahField(forms.DecimalField):
    widget = RupiahWidget

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, (Decimal, int, float)):
            return super().to_python(value)
        return super().to_python(normalize_rupiah_value(value))


def upload_to_supabase(file_obj, vehicle_id):
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    ext = os.path.splitext(file_obj.name)[1] or ".jpg"
    file_path = f"{vehicle_id}/{uuid.uuid4().hex}{ext}"

    url = f"{supabase_url}/storage/v1/object/vehicle-photos/{file_path}"
    headers = {
        "apikey": service_key,
        "Content-Type": file_obj.content_type or "image/jpeg",
        "x-upsert": "true",
    }

    resp = requests.post(url, headers=headers, data=file_obj.read(), timeout=30)
    resp.raise_for_status()

    return f"{supabase_url}/storage/v1/object/public/vehicle-photos/{file_path}"


class VehiclePhotoForm(forms.ModelForm):
    image = forms.FileField(
        label="Pilih gambar",
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "image/*"}),
    )
    order = forms.IntegerField(
        label="Urutan",
        required=False,
        initial=0,
        min_value=0,
    )

    class Meta:
        model = VehiclePhoto
        fields = ["image", "order"]

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            if image.size > MAX_FILE_SIZE:
                raise ValidationError("Ukuran gambar maksimal 1 MB.")
        return image

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get("image")
        if self.instance.pk is None and not image:
            raise ValidationError("Pilih gambar untuk diupload.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        image = self.cleaned_data.get("image")
        if image and not instance.url:
            instance.url = upload_to_supabase(image, instance.vehicle_id)
        if commit:
            instance.save()
        return instance


class RentalForm(forms.ModelForm):
    class Meta:
        model = Rental
        fields = '__all__'
        widgets = {
            'additional_fee_description': forms.Textarea(attrs={
                'rows': 3,
                'style': 'min-height: 100px;',
            }),
        }
