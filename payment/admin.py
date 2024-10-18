from django.contrib import admin

from .models import Payment


# Register your models here.
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "amount",
        "currency",
        "transaction_id",
        "verified",
        "timestamp",
        "expiration_date"
    )


admin.site.register(Payment, PaymentAdmin)
