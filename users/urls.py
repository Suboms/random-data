from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework.urls import path
from users.views import CreateUserViewSet, MyTokenObtainPairView, TokenVerifyView, TokenRefreshView


router = DefaultRouter()
router.register(r"", CreateUserViewSet)

urlpatterns = [
    path("login/", MyTokenObtainPairView.as_view(), name="login"),
    path("login/refresh/", TokenRefreshView.as_view(), name="login-refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]
urlpatterns += router.urls
