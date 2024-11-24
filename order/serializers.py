from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from .models import Order, Subscription


class OrderRequestSerializer(serializers.Serializer):
    subscription = subscription = serializers.SlugRelatedField(
        queryset=Subscription.objects.all(), slug_field="name"
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Example Order",
            value={
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "plan": "string",
                "reference": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "total_amount": "148315",
                "duration": 0,
                "order_status": "string",
                "start_date": "2024-11-17T17:17:03.693Z",
                "end_date": "2024-11-17T17:17:03.693Z",
                "paid": True,
                "created_at": "2024-11-17T17:17:03.693Z",
                "updated_at": "2024-11-17T17:17:03.693Z",
            },
        )
    ]
)
class OrderSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    subscription = serializers.SlugRelatedField(
        queryset=Subscription.objects.all(), slug_field="name"
    )
    reference = serializers.UUIDField(read_only=True)
    total_amount = serializers.DecimalField(
        read_only=True, decimal_places=2, max_digits=10
    )
    order_status = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    end_date = serializers.DateTimeField(read_only=True)
    paid = serializers.BooleanField(read_only=True)

    class SubscriptionSlugRelatedField(serializers.SlugRelatedField):
        def to_internal_value(self, data):
            # Perform a case-insensitive lookup for the subscription
            try:
                return self.get_queryset().get(**{f"{self.slug_field}__iexact": data})
            except Subscription.DoesNotExist:
                raise serializers.ValidationError(
                    f"Object with {self.slug_field}={data} does not exist."
                )

    # Use the custom SubscriptionSlugRelatedField for case-insensitive lookup
    subscription = SubscriptionSlugRelatedField(
        queryset=Subscription.objects.all(), slug_field="name"
    )

    class Meta:
        model = Order
        fields = "__all__"

    # def validate_subscription(self, value):
    #     value = value.title()
    #     print(value)
    #     try:
    #         return Subscription.objects.get(name=value)
    #     except Subscription.DoesNotExist:
    #         raise serializers.ValidationError(
    #             f"Subscription with name '{value}' does not exist."
    #         )

    # def get_fields(self):
    #     fields = super().get_fields()

    #     # Use context to check if we're in the context of a request (e.g., POST request)
    #     request = self.context.get("request", None)

    #     if request and request.method == "POST":
    #         plan_name = request.data.get("subscription")
    #         if plan_name == "Annual":
    #             fields["duration"].read_only = True
    #         else:
    #             fields["duration"].read_only = False

    #     return fields
