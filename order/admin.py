from django.contrib import admin

from .models import Order, Plan


# Register your models here.
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ['created_at']
admin.site.register(Order, OrderAdmin)
admin.site.register(Plan)
