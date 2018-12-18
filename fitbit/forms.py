from django import forms

from .models import UploadFileModel


class UploadFileForm(forms.ModelForm):
    class Meta:
        model = UploadFileModel
        fields = ('file', 'save_path', 'save_name')
