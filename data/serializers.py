from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Payment

User = get_user_model()


class PaymentInitSerializer(serializers.Serializer):
    email = serializers.EmailField()
    amount = serializers.DecimalField(max_digits=17, decimal_places=2, validators=[])
    currency = serializers.CharField()

    def validate_amount(self, value):
        return int(value * 100)


class PaymentVerifySerialzer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Payment
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["currency"] = instance.get_currency_display()
        representation["timestamp"] = instance.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        representation["user"] = instance.user.username
        return representation
