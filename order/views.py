from datetime import timedelta

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from helpers.unique_id import UniqueId

from .models import Order, Plan
from .serializers import OrderSerializer

# Create your views here.


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="create")

    def list(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="list")

    def retrieve(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="retrieve")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="destroy")

    @action(
        methods=["post"], detail=False, url_path="create-order", url_name="create-order"
    )
    def create_order(self, request, *args, **kwargs):
        # Check for unpaid existing order
        unpaid_order = Order.objects.filter(user=request.user, paid=False).first()
        if unpaid_order:
            # Return the existing unpaid order
            serializer = OrderSerializer(unpaid_order)
            return Response(
                {
                    "message": "An unpaid order already exists.",
                    "order": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        # Check for active paid order (end date greater than current date)
        active_paid_order = Order.objects.filter(
            user=request.user, paid=True, end_date__gt=timezone.now()
        ).first()
        if active_paid_order:
            serializer = OrderSerializer(active_paid_order)
            return Response(
                {
                    "message": "An active paid order already exists and has not expired.",
                    "order": serializer.data["id"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Proceed to create a new order if no unpaid or active orders are found
        try:
            serializer = OrderSerializer(
                data=request.data, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)

            sub_plan = serializer.validated_data.get("plan")
            plan_name = sub_plan.name
            duration = (
                12
                if plan_name == "Annual"
                else serializer.validated_data.get("duration")
            )
            price = Plan.objects.get(name=plan_name).price

            # Calculate end date based on duration in months
            end_date = timezone.now() + timedelta(days=30 * duration)

            # Create and save the new order
            order = Order(
                user=request.user,
                reference=UniqueId.generate_id(),
                duration=duration,
                end_date=end_date,
                plan=sub_plan,
                total_amount=duration * price,
            )
            order.save()

            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

        except Plan.DoesNotExist:
            return Response(
                {"error": "The selected plan does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "error": "An error occurred while creating the order.",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
