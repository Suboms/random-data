import json
from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import *
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from helpers.unique_id import UniqueId

from .models import Order, Subscription, SubscriptionType
from .serializers import OrderRequestSerializer, OrderSerializer

# Create your views here.


@extend_schema_view(
    create=extend_schema(exclude=True),
    list=extend_schema(exclude=True),
    # retrieve=extend_schema(exclude=True),
    destroy=extend_schema(exclude=True),
    update=extend_schema(exclude=True),
    partial_update=extend_schema(exclude=True),
)
@extend_schema(
    description="""
The OrderViewSet focuses on user-specific order management while restricting default CRUD operations for better control and security. It ensures that only authenticated users can interact with the viewset and provides the following key features:

1. **Authentication & Permission:**
    - Enforces JWT-based authentication.
    - Restricts access to authenticated users only.

2. **Custom Queryset**
    - Limits the orders visible to the currently authenticated user.

3. **Disabled CRUD Operations**
    - Prevents standard CRUD operations (`create`, `list`, `update`, `destroy`, and `partial_update`) to ensure orders are managed through custom workflows.

4. **Custom Action:** `create_order`
    - Handles the creation of orders or returns existing unpaid or active orders.
    - Checks for:
      - Unpaid orders: Returns the existing unpaid order.
      - Active paid orders: Blocks the creation of a new order if an active paid order exists.
    - Creates a new order only when no unpaid or active orders are found.
    - Handles potential exceptions such as non-existent plans or unexpected errors gracefully. 

""",
    summary="Manages user orders through restricted custom actions.",
)
class OrderViewSet(viewsets.ModelViewSet):
    """
    This viewset manages user orders. Only custom actions are allowed;
    standard CRUD operations are restricted.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            raise NotAuthenticated("User must be authenticated to view this resource.")
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="create")

    def list(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="list")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="destroy")

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="update")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="partial update")

    @extend_schema(
        summary="Retrieves an existing order",
        responses={
            200: OrderSerializer,
            404: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        name="Order Not Found",
                        value=json.loads('{"detail": "Not found."}'),
                    )
                ],
            ),
            401: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        name="Not Authorized",
                        value=json.loads(
                            '{"detail": "Authentication credentials were not provided."}'
                        ),
                    )
                ],
            ),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @extend_schema(
        summary="Creates an order",
        request=OrderRequestSerializer,
        responses={
            200: OrderSerializer,
            201: OpenApiResponse(response=OrderSerializer),
            400: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Validation or state-related errors",
                examples=[
                    OpenApiExample(
                        name="Active Order",
                        value=json.loads(
                            json.dumps(
                                {
                                    "message": "An unpaid order already exists.",
                                    "order": OrderSerializer().data,
                                }
                            )
                        ),
                        description="Occurs when there is already an unpaid order for the user.",
                    ),
                    OpenApiExample(
                        name="Order not expired",
                        value=json.loads(
                            json.dumps(
                                {
                                    "message": "An active paid order already exists and has not expired.",
                                    "order": OrderSerializer().data,
                                },
                            )
                        ),
                        description="Returned when the user has an active paid order that is still valid.",
                    ),
                    OpenApiExample(
                        name="Plan does not exist",
                        value=json.loads(
                            json.dumps({"error": "The selected plan does not exist."})
                        ),
                        description="Occurs when the selected plan ID is invalid or not found.",
                    ),
                ],
            ),
            500: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Server-side errors.",
                examples=[
                    OpenApiExample(
                        name="Unknown Exception",
                        value=json.loads(
                            """{"error": "An error occurred while creating the order.",\n"details": "str(e)"}""",
                        ),
                        description="Indicates an unexpected server error during order creation.",
                        status_codes=[500],
                    )
                ],
            ),
        },
    )
    @action(
        methods=["post"], detail=False, url_path="create-order", url_name="create-order"
    )
    def create_order(self, request, *args, **kwargs):
        """
        Creates a new order or return an existing unpaid or active order
        """

        user = request.user
        unpaid_order = Order.objects.filter(user=user, paid=False).first()
        if unpaid_order:
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

            subscription = serializer.validated_data.get("subscription")

            if subscription.name == SubscriptionType.MONTHLY:
                duration_days = 30
            elif subscription.name == SubscriptionType.ANNUAL:
                duration_days = 365
            else:
                return Response(
                    {"error": "Invalid subscription type."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            price = subscription.price

            # Calculate end date based on duration in months
            end_date = timezone.now() + timedelta(days=duration_days)

            # Create and save the new order
            order = Order(
                user=request.user,
                reference=UniqueId.generate_id(),
                end_date=end_date,
                subscription=subscription,
                total_amount=price,
            )
            order.save()

            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

        except Subscription.DoesNotExist:
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
