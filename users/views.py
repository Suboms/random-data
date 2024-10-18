from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from helpers.unique_id import UniqueId

from .serializers import CreateUserSerializer

User = get_user_model()

# Create your views here.


class CreateUserViewSet(ModelViewSet):
    name = "CreateUserViewSet"
    serializer_class = CreateUserSerializer
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="create")

    def list(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="list")

    def retrieve(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="retrieve")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="destroy")

    @action(methods=["post"], detail=False, url_path="signup", url_name="signup")
    def signup(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = User()
            
            user.username = serializer.validated_data.get("username")
            user.email = serializer.validated_data.get("email")
            user.first_name = serializer.validated_data.get("first_name")
            user.last_name = serializer.validated_data.get("last_name")
            slug = UniqueId.generate_id()
            user.slug = slug
            user.set_password(serializer.validated_data.get("password"))
            user.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        try:
            token = super().get_token(user)

            # Add custom claims
            token["username"] = user.username
            # Add more custom claims as needed

            return token
        except RuntimeError:
            return Response({"Error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            raise Exception(f"Error in token creation: {str(e)}")


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    # renderer_classes  = [BrowsableAPIRenderer, JSONRenderer]

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            token = serializer.validated_data

            return Response(token, status=status.HTTP_200_OK)
        except RuntimeError:
            return Response({"Error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"Error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
