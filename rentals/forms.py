import os
import uuid
import requests
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from .models import VehiclePhoto, MAX_PHOTOS_PER_VEHICLE, MAX_FILE_SIZE


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
