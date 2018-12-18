from django.http import HttpResponseRedirect
from django.shortcuts import render
from .forms import UploadFileForm
from django.core.files.storage import FileSystemStorage

from .fitbit_data import FitbitData

f_data = FitbitData()


def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/')
    else:
        form = UploadFileForm()
    return render(request, 'fitbit/upload.html', {'form': form})
