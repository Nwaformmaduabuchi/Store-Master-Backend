from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ListVariantView

router = DefaultRouter()


router.register(r'variants', ListVariantView, basename='variants')

urlpatterns = router.urls