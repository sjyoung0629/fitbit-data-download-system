from django.db import models


class UploadFileModel(models.Model):
    file = models.FileField(null=True, blank=True)
    save_path = models.FilePathField(path='fitbit', allow_files=False, allow_folders=True)
    save_name = models.CharField(verbose_name='저장 파일명', max_length=10, default='.xlsx')
