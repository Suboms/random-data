from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
import requests
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from order.models import Order

from .models import Payment

# Create your views here.
# class PaymentViewSets(viewsets.ViewSet):

#     @action(methods=["get"], detail=False, url_name="payment")
#     def create_payment(self, request, *args, **kwargs):
#         try:
#             order = Order.objects.get(user=request.user)
#         except Order.DoesNotExist:
#             return Response(
#                 {"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND
#             )
#         if order.paid == False:
#             amount = order.total_amount
#             email = order.user.email

#             payment_data = {
#                 "email": email,
#                 "amount": int(amount * 100),
#             }

#             response = requests.post(
#                 "https://api.paystack.co/transaction/initialize",
#                 json=payment_data,
#                 headers={
#                     "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
#                     "Content-Type": "application/json",
#                 },
#             )

#             if response.status_code == 200:
#                 payment_info = response.json()
#                 transaction_id = payment_info["data"]["reference"]

#                 payment = Payment.objects.create(
#                     order=order,
#                     amount=amount,
#                     currency="NGN",
#                     verified=False,
#                     transaction_id=transaction_id,
#                 )
#                 return Response(payment_info["data"], status=status.HTTP_200_OK)

#             return Response(response.json(), status=response.status_code)


class PaymentViewSets(viewsets.ViewSet):

    @action(methods=["get"], detail=False, url_name="payment")
    def create_payment(self, request, *args, **kwargs):
        # Attempt to get the user's order
        try:
            order = Order.objects.get(user=request.user)
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


class PaystackWebhookView(APIView):
    @csrf_exempt
    def post(self, request):
        event = request.data.get("event")
        data = request.data.get("data")

        if event == "charge.success":
            transaction_id = data.get("reference")
            try:
                payment = Payment.objects.get(transaction_id=transaction_id)
                order = payment.order

                # Handling the 'paid_at' field
                paid_at = data.get("paid_at")
                try:
                    # Try parsing with microseconds
                    paid_at_datetime = datetime.strptime(
                        paid_at, "%Y-%m-%dT%H:%M:%S.%fZ"
                    )
                except ValueError:
                    # Fallback for when there are no microseconds
                    paid_at_datetime = datetime.strptime(
                        paid_at, "%Y-%m-%dT%H:%M:%S.%fZ"[:-3]
                    )

                # Convert the naive datetime to an aware datetime with the current timezone
                paid_at_datetime = timezone.make_aware(
                    paid_at_datetime, dt_timezone.utc
                )
                paid_at_datetime = timezone.localtime(paid_at_datetime)

                if order.plan.name == "Annual":
                    payment.expiration_date = paid_at_datetime + relativedelta(years=1)
                else:
                    duration = order.duration
                    payment.expiration_date = paid_at_datetime + relativedelta(
                        months=duration
                    )
                payment.timestamp = paid_at_datetime
                payment.verified = True
                payment.save()
                order.paid = True
                order.user.is_paiduser = True
                order.end_date = paid_at_datetime + relativedelta(years=1)
                order.order_status = "Completed"
                order.save()

            except Payment.DoesNotExist:
                return Response(
                    {"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND
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
