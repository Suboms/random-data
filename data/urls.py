from rest_framework.urls import path

from data.views import DummyData

urlpatterns = [
    # path("random/", RandomData.as_view(), name="random-data"),
    path("dummy/", DummyData.as_view(), name="dummy-data"),
    # path("payment/", PaymentInitView.as_view(), name="payment"),
    # path("payment/callback/", PaymentCallbackView.as_view(), name="payment-callback"),
]
