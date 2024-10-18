from django.conf import settings
from django.db import models

from commons.models import TimeStampedModel

# Create your models here.


class OrderStatus(models.TextChoices):
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

class PlanChoice(models.TextChoices):
    MONTHLY = "Monthly"
    ANNUALY = "Annualy"

class Plan(TimeStampedModel):
    name = models.CharField(max_length=20, default="Annual")
    price = models.DecimalField(max_digits=10, decimal_places=2)  # price for the plan

    def __str__(self) -> str:
        return f'{self.name}'

class Order(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False
    )
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, null=False)
    reference = models.UUIDField(max_length=100, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Total amount for the order
    duration = models.IntegerField()
    paid = models.BooleanField(default=False)
    order_status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()

    class Meta:
        ordering = ("created_at",)
    def __str__(self):
        return f"Order {self.reference}"