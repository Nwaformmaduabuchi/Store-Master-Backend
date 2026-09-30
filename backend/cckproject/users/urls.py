from django.contrib import admin
from django.urls import path, include
from .views import LogOutView, LoginView, RegisterView, CreateCompany, RefreshTokenView, GetUserView


urlpatterns = [
    
    path("login/", LoginView.as_view(), name="login"),
    path("login/refresh/", RefreshTokenView.as_view(), name="login_refresh"),
    path("logout/", LogOutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path("register/company/", CreateCompany.as_view(), name="create_company"),
    path("user/", GetUserView.as_view(), name="get user"),
]