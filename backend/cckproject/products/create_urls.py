from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CreateStockView, UpdateVariantView

router = DefaultRouter()

router.register(r'stock', CreateStockView, basename='create-stock')
router.register(r'edit', UpdateVariantView, basename='update-variant')


urlpatterns = router.urls
