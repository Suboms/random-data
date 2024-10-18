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

    @action(methods=["post"], detail=False, url_path="create-order", url_name="create-order")
    def create_order(self, request, *args, **kwargs):
        price = Plan.objects.first().price
        existing_order = Order.objects.filter(user=request.user, paid=False).first()
        if existing_order:
            # Serialize the existing order and return it in a response
            serializer = OrderSerializer(existing_order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        try:
            # serializer = self.get_serializer(data = request.data)
            serializer = OrderSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            
            sub_plan = serializer.validated_data.get("plan")
            if sub_plan.name == "Annual":
                duration = 12
            else:
                duration = serializer.validated_data.get('duration')
            end_date = timezone.now() + timedelta(days=30 * duration)
            order = Order(
                user = serializer.validated_data.get('user'),
                reference = UniqueId.generate_id(),
                duration = duration,
                end_date = end_date,
                plan = serializer.validated_data.get("plan"),
                total_amount = duration * price
            )
            order.save()
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)
