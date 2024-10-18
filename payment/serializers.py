from rest_framework import serializers

from order.models import Order

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, validators=[])
    currency = serializers.CharField(read_only=True)
    transaction_id = serializers.CharField(read_only=True)
    verified = serializers.BooleanField(read_only=True)
    class Meta:
        model = Payment
        fields = "__all__"
