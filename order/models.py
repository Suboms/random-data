from django.conf import settings
from django.db import models

from commons.models import TimeStampedModel

# Create your models here.


class OrderStatus(models.TextChoices):
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class SubscriptionType(models.TextChoices):
    MONTHLY = "Monthly"
    ANNUAL = "Annual"


class Subscription(models.Model):
    name = models.CharField(choices=SubscriptionType.choices, max_length=20)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name.capitalize()} Subscription"

    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"


class Order(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reference = models.UUIDField(unique=True, editable=False)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.BooleanField(default=False)
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="orders"
    )
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"Order {self.reference}"
