from django.conf import settings
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.generics import GenericAPIView
from rest_framework.exceptions import AuthenticationFailed
from helpers.unique_id import UniqueId

from .serializers import CreateUserSerializer

User = get_user_model()

# Create your views here.


@extend_schema_view(
    create=extend_schema(exclude=True),
    list=extend_schema(exclude=True),
    retrieve=extend_schema(exclude=True),
    destroy=extend_schema(exclude=True),
    update=extend_schema(exclude=True),
    partial_update=extend_schema(exclude=True),
)
class CreateUserViewSet(ModelViewSet):
    """
    The CreateUserViewSet is a specialized viewset for user registration, allowing new users to sign up through the signup action.
    """

    serializer_class = CreateUserSerializer
    queryset = User.objects.all()
    permission_classes = []
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="create")

    def list(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="list")

    def retrieve(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="retrieve")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="destroy")

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="update")

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="partial update")

    @extend_schema(
        summary="A custom action that handles user creation",
        responses={
            (201, "application/json"): {
                "description": "User Creation",
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "email": {"type": "string"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "is_paiduser": {"type": "boolean"},
                },
                "example": {
                    "username": "string",
                    "email": "user@example.com",
                    "first_name": "string",
                    "last_name": "string",
                    "is_paiduser": True,
                },
            },
            (400, "application/json"): {
                "description": "Bad Request",
                "type": "object",
                "example": {"errors": "error detail"},
            },
            (500, "application/json"): {
                "description": "Server Error",
                "type": "object",
                "example": {
                    "error": "An unexpected error occurred",
                    "details": "error message",
                },
            },
        },
    )
    @action(methods=["post"], detail=False, url_path="signup", url_name="signup")
    def signup(self, request, *args, **kwargs):
        """
        This action allows new users to register by providing their username, email, first name, last name, and password. The action performs the following steps:
        - Validates the input data using the CreateUserSerializer.
        - Creates a new User instance with the provided details.
        - Generates a unique slug for the user.
        - Saves the new user to the database and returns the user data with a 201 Created status.
        - Handles validation errors and general exceptions, returning appropriate error messages and status codes.
        """

        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = User(
                username=serializer.validated_data.get("username"),
                email=serializer.validated_data.get("email"),
                first_name=serializer.validated_data.get("first_name"),
                last_name=serializer.validated_data.get("last_name"),
                slug=UniqueId.generate_id(),
            )
            user.set_password(serializer.validated_data.get("password"))
            user.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as validation_error:
            return Response(
                {"errors": validation_error.detail}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        try:
            token = super().get_token(user)

            # Add custom claims
            token["username"] = user.username
            # Add more custom claims as needed

            return token
        except RuntimeError as e:
            return Response({"Error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            raise Exception(f"Error in token creation: {str(e)}")


@extend_schema(
    responses={
        (200, "application/json"): {
            "description": "User Login View",
            "type": "object",
            "properties": {"refresh": {"type": "string"}, "access": {"type": "string"}},
            "example": {
                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTczMjk5NzQ1MywiaWF0IjoxNzMyMzkyNjUzLCJqdGkiOiI2NTA2ZGViMGJkOWM0ZmM4OWU5Y2FkODk0N2NlMjE5MyIsInVzZXJfaWQiOiIwZWFkMDJhNmJiZWY0ZjUzODJhNjBjZWJmZjBkZmIzMyIsInVzZXJuYW1lIjoiYWRtaW4ifQ.q_ms6T7C5c0Tq7W9Pi5AoDRLrSqKoQ-XPvQag8p-QVo",
                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYzODQyMjUzLCJpYXQiOjE3MzIzOTI2NTMsImp0aSI6IjVlNDcxMDY2NGExNzQxYTk4MThhMzIxOTUyNDU2OWNkIiwidXNlcl9pZCI6IjBlYWQwMmE2YmJlZjRmNTM4MmE2MGNlYmZmMGRmYjMzIiwidXNlcm5hbWUiOiJhZG1pbiJ9.gyjRRu3FTNntW8PRC8Q4ALtDrWJx_KV6zSzO7bhUYbI",
            },
        }
    }
)
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    # renderer_classes  = [BrowsableAPIRenderer, JSONRenderer]

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            token = serializer.validated_data
            return Response(token, status=status.HTTP_200_OK)
        
        except AuthenticationFailed as auth_error:
            # Handle authentication errors explicitly
            return Response({"error": "Authentication failed", "details": str(auth_error)}, status=status.HTTP_401_UNAUTHORIZED)
        
        except RuntimeError as runtime_error:
            # Handle runtime-specific issues
            return Response({"error": "Runtime error", "details": str(runtime_error)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as general_error:
            # Catch-all for unexpected errors
            return Response({"error": "An unexpected error occurred", "details": str(general_error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class TokenVerifyView(APIView):
    def post(self, request, *args, **kwargs):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Token is Required"}, status=400)
        try:
            validated_data = TokenBackend(
                algorithm="HS256",
                signing_key=settings.SECRET_KEY,
                verifying_key=settings.SECRET_KEY,
            ).decode(token, verify=True)
            return Response({"Valid": True, "data": validated_data}, status=200)
        except AuthenticationFailed as e:
            return Response({"valid": False, "error": str(e)}, status=401)
        except TokenError as e:
            return Response({"valid": False, "error": str(e)}, status=401)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)}, status=500
            )

class TokenRefreshView(GenericAPIView):
    serializer_class = TokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=200)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)}, status=500
            )


    