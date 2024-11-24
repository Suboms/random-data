from django.contrib import admin

from .models import Order, Subscription


# Register your models here.
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "created_at"]


admin.site.register(Order, OrderAdmin)
admin.site.register(Subscription)
