from urllib import response

from django.conf import settings
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework_simplejwt.views import  TokenObtainPairView , TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from .permisions import HasCompany
from .services import CompanyService
from .serializers import CompanySerializer, UserDataSerializer
import traceback
from .services import create_user
from .serializers import LoginSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request,*args, **kwargs):
        response = super().post(request,*args, **kwargs)
        response.data["detail"] = "Login Successful"
        return response

class RefreshTokenView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        refresh = request.COOKIES.get("refresh")
        if not refresh:
            return super().post(request, *args, **kwargs)
        request.data["refresh"] = refresh
        
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            return response

class GetUserView(GenericAPIView):
    permission_classes = [IsAuthenticated, HasCompany]
    serializer_class = UserDataSerializer
    
    def get(self, request, *args, **kwargs):
        
        data = {
        "user": request.user,
        "company": request.user.company,
        }
        serializer = self.get_serializer(data)
        return Response(serializer.data)

class LogOutView(GenericAPIView):
    permission_classes = [IsAuthenticated, HasCompany]
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh")
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        response = Response(
            {"detail": "Logout successful"},
            status=HTTP_200_OK,
            )

        response.delete_cookie("access")
        response.delete_cookie("refresh")

        return response

class RegisterView(GenericAPIView):
    permission_classes = [AllowAny] 
    authentication_classes = []
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        print(request.data)
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            print("validate_data is =", serializer.validated_data)
            user = create_user(
                data=serializer.validated_data
            )
        except Exception as e:
                print("TYPE:", type(e))
                print("ERROR:", repr(e))
                traceback.print_exc()

        return Response(
            {
                "message": "user successfully registered",
                "data": UserSerializer(user).data,
            },
            status=HTTP_201_CREATED,
        )

        

class CreateCompany(GenericAPIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    serializer_class = CompanySerializer
    
    def post(self, request,*args,**kwargs):
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        company = CompanyService.create_company(data=serializer.validated_data, owner=request.user)

        return Response(
                    {
                        "message": "company successfully registered",
                        "data": CompanySerializer(company).data,
                    },
                    status=HTTP_201_CREATED,
                )
    
                