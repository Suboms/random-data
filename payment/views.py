import datetime
import hashlib
import hmac
import json
from datetime import timezone as dt_timezone

import requests
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.timezone import localtime, make_aware
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from order.models import Order

from .models import Order, Payment


@extend_schema(
    responses={
        (200, "application/json"): {
            "type": "object",
            "example": {
                "authorization_url": "https://checkout.paystack.com/vfzz3m2reu16ma4",
                "access_code": "vfzz3m2reu16ma4",
                "reference": "vw689n4rqe",
            },
            "description": "Response indicating successful creation of a payment authorization. Includes a URL for payment, an access code for verification, and a unique reference for tracking the transaction.",
        },
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Error responses indicating issues with the client's request.",
            examples=[
                OpenApiExample(
                    name="Invalid order amount",
                    value=json.loads(json.dumps({"error": "Invalid order amount."})),
                    description="Occurs when the specified order amount does not meet validation requirements.",
                    response_only=True,
                ),
                OpenApiExample(
                    name="Paid Order",
                    value=json.loads(json.dumps({"error": "Order already paid."})),
                    description="Indicates that the order has already been processed and cannot be paid again.",
                    response_only=True,
                ),
            ],
        ),
        (404, "application/json"): {
            "type": "object",
            "example": {"error": "Order not found."},
            "description": "Indicates that the requested order could not be found in the system. This error occurs when the order ID provided does not exist or has been deleted.",
        },
        (503, "application/json"): {
            "type": "object",
            "example": {
                "error": "Payment service unavailable.",
                "details": "error message",
            },
            "description": "Occurs when the payment service is temporarily unavailable. This may be due to server maintenance or network issues. The 'details' field provides additional information on the error, if available.",
        },
    },
    summary="Handles the creation of a payment for a user's order.",
    description="""
The `create_payment` method in this viewset handles the payment initiation process for a user's order. The view performs the following steps:\n
1. **Order Retrieval:** The method first attempts to retrieve an unpaid order for the authenticated user. If no such order exists, a `404 Not Found` error is returned.\n
2. **Order Validation:** If the order is found, it checks whether the order's amount is valid (greater than zero). If the amount is invalid, a `400 Bad Request error` is returned with a message indicating the issue.\n
3. **Payment Data Preparation:** If the order is valid, the method prepares payment data, including the user's email and the order amount (converted to kobo, the smallest unit of NGN).\n
4. **Paystack API Integration:** The method then attempts to interact with Paystack's API by making a POST request to initialize the payment. If the request fails due to network or API issues, a `503 Service Unavailable error` is returned with the details of the exception.\n
5. **Payment Creation:** If Paystack responds successfully, a payment record is created in the database, and the transaction reference is used to track the payment.\n
6. **Response:** If everything is successful, the Paystack response containing payment details is returned with a `200 OK` status. If the Paystack API returns an error, that error is propagated with the appropriate HTTP status code.\n
This view ensures that users can only make payments for valid, unpaid orders and handles any errors that may arise from the Paystack API integration or the order's payment status.
""",
)
class PaymentViewSets(viewsets.ViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @action(methods=["get"], detail=False, url_name="payment")
    def create_payment(self, request, *args, **kwargs):
        # Attempt to get the user's order
        try:
            order = Order.objects.get(user=request.user, paid=False)
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Only proceed if the order is not yet paid
        if not order.paid:
            amount = order.total_amount
            if amount <= 0:
                return Response(
                    {"error": "Invalid order amount."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            email = order.user.email

            # Prepare the data for the Paystack API call
            payment_data = {
                "email": email,
                "amount": int(
                    amount * 100
                ),  # Ensure amount is in kobo (smallest denomination of NGN)
            }

            try:
                # Send request to Paystack API
                response = requests.post(
                    "https://api.paystack.co/transaction/initialize",
                    json=payment_data,
                    headers={
                        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                        "Content-Type": "application/json",
                    },
                )
            except requests.RequestException as e:
                return Response(
                    {"error": "Payment service unavailable.", "details": str(e)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            # Check Paystack response status
            if response.status_code == 200:
                payment_info = response.json()
                transaction_id = payment_info["data"]["reference"]

                # Create a Payment record in your database
                payment = Payment.objects.create(
                    order=order,
                    amount=amount,
                    currency="NGN",
                    verified=False,
                    transaction_id=transaction_id,
                    expiration_date=timezone.now(),
                )
                return Response(payment_info["data"], status=status.HTTP_200_OK)

            # Handle non-200 status codes returned from Paystack
            return Response(response.json(), status=response.status_code)

        return Response(
            {"error": "Order already paid."}, status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Handles Paystack webhook notifications to update the payment and order status on the server when a payment is successful or failed.",
    description="""
The `PaystackWebhookView` is an API view that processes incoming webhook notifications from Paystack, specifically for payment events like charge success and charge failure. This view is designed to be set as the webhook URL in the Paystack dashboard, so Paystack can notify the server of transaction updates. The view performs the following steps:\n
1. **Event Handling:** The view first checks the event type in the incoming request to determine whether the payment has been successfully completed (`charge.success`) or failed (`charge.failed`).\n
2. **Charge Success:**
    - Verification Request: If the event is a successful charge (`charge.success`), the view extracts the transaction ID from the webhook data and makes a request to Paystack's verification endpoint to check if the payment is indeed successful.\n
    - Payment Validation: If Paystack returns a successful verification (`status == "success"`), the view looks up the corresponding payment in the database using the transaction ID.\n
    - Order and Payment Update: Once the payment is verified, the view updates the payment record with the correct timestamp, expiration date, and marks it as verified. It also updates the order status, marks the order as paid, and updates the user's subscription status (e.g., `is_paiduser = True`).\n
      - If the order is associated with an annual plan, the payment's expiration date is set to one year from the payment timestamp.\n
      - For non-annual plans, the expiration date is set.\n
3. **Charge Failure:**
    - If the event is a failed charge (`charge.failed`), the view updates the payment status to "failed" in the database, allowing the system to track the failure.\n
    - If no payment corresponding to the transaction ID is found, it returns a `404 Not Found` response indicating the payment does not exist. \n
4. **Error Handling:**
    - The view ensures that if no payment record is found for the given transaction ID (whether for a successful or failed payment), it returns a `404 Not Found` response with an error message.\n
5. **Response:**
    - After processing the webhook, the view sends a `200 OK` response back to Paystack, confirming that the webhook has been successfully received and processed.\n

## Example Workflow:
- **Charge Success:** When Paystack notifies the server that a payment has been successfully completed, the server verifies the payment, updates the user's subscription status, and ensures the correct expiration date for the subscription.\n
- **Charge Failure:** If Paystack notifies the server of a failed payment, the server marks the payment as failed, allowing the system to take appropriate action (e.g., retrying the payment or notifying the user).\n
## Use Case:
This view serves as the backend component that listens for Paystack webhook events. When a user completes a payment via Paystack, the webhook is triggered, notifying the server of the payment status. The server then updates its internal payment and order records accordingly. For proper integration, users must configure this URL as their webhook URL in the Paystack dashboard.\n
""",
    request={
        "application/json": {
            "description": "User credentials",
            "type": "object",
            "properties": {
                "event": {"type": "string"},
                "data": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "format": "int64"},
                        "domain": {"type": "string"},
                        "status": {"type": "string"},
                        "reference": {"type": "string"},
                        "amount": {"type": "integer", "format": "int64"},
                        "message": {"type": "string"},
                        "gateway_response": {"type": "string"},
                        "paid_at": {"type": "string", "format": "date"},
                        "created_at": {"type": "string", "format": "date"},
                        "channel": {"type": "string"},
                        "currency": {"type": "string"},
                        "ip_address": {"type": "string"},
                        "metadata": {"type": "string"},
                        "fees_breakdown": {"type": "string"},
                        "log": {"type": "string"},
                        "fees": {"type": "integer", "format": "int64"},
                        "fees_split": {"type": "string"},
                        "authorization": {
                            "type": "object",
                            "properties": {
                                "authorization_code": {"type": "string"},
                                "bin": {"type": "string"},
                                "last4": {"type": "string"},
                                "exp_month": {"type": "string"},
                                "exp_year": {"type": "string"},
                                "channel": {"type": "string"},
                                "card_type": {"type": "string"},
                                "bank": {"type": "string"},
                                "country_code": {"type": "string"},
                                "brand": {"type": "string"},
                                "reusable": {
                                    "type": "boolean",
                                },
                                "signature": {"type": "string"},
                                "account_name": {"type": "string"},
                                "customer": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer", "format": "int64"},
                                        "first_name": {"type": "string"},
                                        "last_name": {"type": "string"},
                                        "email": {"type": "string"},
                                        "customer_code": {"type": "string"},
                                        "phone": {"type": "string"},
                                        "metadata": {"type": "string"},
                                        "risk_action": {"type": "string"},
                                        "international_format_phone": {
                                            "type": "string"
                                        },
                                    },
                                },
                                "plan": {"type": "object"},
                                "subaccount": {"type": "object"},
                                "split": {"type": "object"},
                                "order_id": {"type": "string"},
                                "paidAt": {"type": "string"},
                                "requested_amount": {
                                    "type": "integer",
                                    "format": "int64",
                                },
                                "pos_transaction_data": {"type": "object"},
                                "source": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "api"},
                                        "source": {"type": "string"},
                                        "entry_point": {"type": "string"},
                                        "identifier": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "required": ["event", "data"],
            "example": {
                "event": "charge.success",
                "data": {
                    "id": 4399417754,
                    "domain": "test",
                    "status": "success",
                    "reference": "swpb31e6fa",
                    "amount": 3000000,
                    "message": None,
                    "gateway_response": "Successful",
                    "paid_at": "2024-11-21T20:34:54.000Z",
                    "created_at": "2024-11-21T20:34:33.000Z",
                    "channel": "card",
                    "currency": "NGN",
                    "ip_address": "102.88.81.80",
                    "metadata": "",
                    "fees_breakdown": None,
                    "log": None,
                    "fees": 55000,
                    "fees_split": None,
                    "authorization": {
                        "authorization_code": "AUTH_5j9wqm00vy",
                        "bin": "408408",
                        "last4": "4081",
                        "exp_month": "12",
                        "exp_year": "2030",
                        "channel": "card",
                        "card_type": "visa ",
                        "bank": "TEST BANK",
                        "country_code": "NG",
                        "brand": "visa",
                        "reusable": True,
                        "signature": "SIG_urGK5s8HGwrflRMacEG4",
                        "account_name": None,
                    },
                    "customer": {
                        "id": 198260291,
                        "first_name": None,
                        "last_name": None,
                        "email": "admin@admin.com",
                        "customer_code": "CUS_rz6do19lra3bzsy",
                        "phone": None,
                        "metadata": None,
                        "risk_action": "default",
                        "international_format_phone": None,
                    },
                    "plan": {},
                    "subaccount": {},
                    "split": {},
                    "order_id": None,
                    "paidAt": "2024-11-21T20:34:54.000Z",
                    "requested_amount": 3000000,
                    "pos_transaction_data": None,
                    "source": {
                        "type": "api",
                        "source": "merchant_api",
                        "entry_point": "transaction_initialize",
                        "identifier": None,
                    },
                },
            },
        }
    },
    responses={
        (200, "application/json"): {
            "description": "WebHook Successfully recieved",
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "example": {"message": "Webhook received"},
        },
        403: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="",
            examples=[
                OpenApiExample(
                    name="Missing Signature",
                    value=json.loads(json.dumps({"error": "Missing signature."})),
                ),
                OpenApiExample(
                    name="Invalid Signature",
                    value=json.loads(json.dumps({"error": "Invalid signature."})),
                ),
            ],
        ),
        (404, "application/json"): {
            "description": "Payment Does Not Exist",
            "type": "object",
            "properties": {"error": {"type": "string"}},
            "example": {"error": "Payment not found."},
        },
        (500, "application/json"): {
            "description": "Server Error",
            "type": "object",
            "properties": {"error": {"type": "string"}, "detail": {"type": "string"}},
            "example": {
                "error": "An Error oocurd whilst processing payment",
                "detail": "error message",
            },
        },
    },
)
@method_decorator(csrf_exempt, name="dispatch")
class PaystackWebhookView(APIView):
    def post(self, request):
        # Validate Paystack signature
        paystack_signature = request.headers.get("x-paystack-signature")
        payload = request.body
        secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")

        if not paystack_signature:
            return Response(
                {"error": "Missing signature."}, status=status.HTTP_403_FORBIDDEN
            )

        # Compute the signature locally
        computed_signature = hmac.new(secret, payload, hashlib.sha512).hexdigest()
        if not hmac.compare_digest(computed_signature, paystack_signature):
            return Response(
                {"error": "Invalid signature."}, status=status.HTTP_403_FORBIDDEN
            )

        event = request.data.get("event")
        data = request.data.get("data")

        if event == "charge.success":
            transaction_id = data.get("reference")
            try:
                # Verify transaction with Paystack
                response = requests.get(
                    f"https://api.paystack.co/transaction/verify/{transaction_id}",
                    headers={
                        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                        "Content-Type": "application/json",
                    },
                )
                if response.status_code == 200:
                    payment_verification = response.json()
                    payment_is_valid = payment_verification["data"]["status"]
                    if payment_is_valid == "success":
                        payment = Payment.objects.get(transaction_id=transaction_id)
                        order = payment.order

                        # Parse the `paid_at` field
                        paid_at = data.get("paid_at")
                        try:
                            paid_at_datetime = datetime.datetime.strptime(
                                paid_at, "%Y-%m-%dT%H:%M:%S.%fZ"
                            )
                        except ValueError:
                            paid_at_datetime = datetime.datetime.strptime(
                                paid_at, "%Y-%m-%dT%H:%M:%S.%fZ"[:-3]
                            )
                        paid_at_datetime = make_aware(paid_at_datetime)
                        paid_at_datetime = localtime(paid_at_datetime)

                        # Update payment and order information
                        if order.subscription.name == "Annual":
                            payment.expiration_date = paid_at_datetime + relativedelta(
                                years=1
                            )
                        else:
                            payment.expiration_date = paid_at_datetime + relativedelta(
                                months=1
                            )
                        payment.timestamp = paid_at_datetime
                        payment.verified = True
                        payment.save()
                        Payment.objects.filter(order=order).exclude(
                            id=payment.id
                        ).delete()
                        order.paid = True
                        order.user.is_paiduser = True
                        order.end_date = paid_at_datetime + relativedelta(years=1)
                        order.order_status = "Completed"
                        order.save()

            except Payment.DoesNotExist:
                return Response(
                    {"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {
                        "error": "An Error oocurd whilst processing payment",
                        "detail": str(e),
                    },
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        elif event == "charge.failed":
            transaction_id = data.get("id")
            try:
                payment = Payment.objects.get(transaction_id=transaction_id)
                payment.status = "failed"
                payment.save()
            except Payment.DoesNotExist:
                return Response(
                    {"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND
                )

        return Response({"message": "Webhook received"}, status=status.HTTP_200_OK)
