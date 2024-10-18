from django.db import models

from order.models import Order


# Create your models here.
class CurrencyChoice(models.TextChoices):
    NGN = "NGN"
    USD = "USD"


class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=False)
    amount = models.DecimalField(max_digits=17, decimal_places=2)
    currency = models.CharField(choices=CurrencyChoice.choices, max_length=20)
    transaction_id = models.CharField(max_length=100, unique=True)
    verified = models.BooleanField(default=False)
    expiration_date = models.DateTimeField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Payment for {self.order.user.username}"

    class Meta:
        verbose_name_plural = "Payments"
        ordering = ["timestamp"]