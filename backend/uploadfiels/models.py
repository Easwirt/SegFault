from django.db import models
from django.contrib.auth.models import User


class UserUpload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='csv/')
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField()  # in bytes

    def __str__(self):
        return f"{self.user.username} - {self.original_filename}"

    class Meta:
        ordering = ['-uploaded_at']