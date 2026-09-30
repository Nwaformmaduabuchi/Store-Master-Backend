from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ListSaleView
from.views import StockMovementView, DeleteSaleView, PatchSaleView, UpdateSaleView, CustomerView , PaymentView

router = DefaultRouter()
router.register(r'sale', ListSaleView, basename='list-sale')
router.register(r'del', DeleteSaleView, basename='del-sale')
router.register(r'patch', PatchSaleView, basename='patch-sale')
router.register(r'update', UpdateSaleView, basename='update-sale')
router.register(r'history', StockMovementView, basename='history')
router.register(r'customer', CustomerView, basename='customer')
router.register(r'payments', PaymentView, basename='payment')


urlpatterns = router.urls
