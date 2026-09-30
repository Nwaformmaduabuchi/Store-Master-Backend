from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CreateSaleView

router = DefaultRouter()

router.register(r'sale', CreateSaleView, basename='create-sale')



urlpatterns = router.urls
