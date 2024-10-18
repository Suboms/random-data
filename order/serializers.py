from rest_framework import serializers

from .models import Order, Plan


class PlanSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(read_only=True, decimal_places=2, max_digits=10)

    class Meta:
        model = Plan
        fields = ["name", "price"]


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    plan = serializers.SlugRelatedField(queryset=Plan.objects.all(), slug_field="name")
    reference = serializers.UUIDField(read_only=True)
    total_amount = serializers.DecimalField(
        read_only=True, decimal_places=2, max_digits=10
    )
    duration = serializers.IntegerField()
    order_status = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    end_date = serializers.DateTimeField(read_only=True)
    paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()

        # Use context to check if we're in the context of a request (e.g., POST request)
        request = self.context.get("request", None)

        if request and request.method == "POST":
            plan_name = request.data.get("plan")
            if plan_name == "Annual":
                fields["duration"].read_only = True
            else:
                fields["duration"].read_only = False

        return fields


# fields = [
#     "id",
#     "reference",
#     "user",
#     "total_amount",
#     "duration",
#     "paid",
#     "order_status",
#     "created_at",
#     "start_date",
#     "end_date"
# ]
