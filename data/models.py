from django.conf import settings
from django.db import models

# Create your models here.





class UserSavedData(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False
    )
    data = models.JSONField(default=list)

    def __str__(self) -> str:
        return self.user

    class Meta:
        verbose_name_plural = "User Data"
