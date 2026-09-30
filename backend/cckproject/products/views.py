from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet

from .models import Product, Variant, Category
from .serialisers import CreateStockSerializer, ProductSerializer, VariantSerializer, VariantUpdateSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from users.authentication import CustomJWTAuthentication
from .services import create_stock, delete_variant, updated_variant
from rest_framework.response import Response
from rest_framework import status
from users.permisions import HasCompany


# Create your views here.

class CreateStockView(ModelViewSet):
    permission_classes = [IsAuthenticated, HasCompany]
    queryset = Product.objects.all()
    serializer_class = CreateStockSerializer
    
    def create(self, request, *args, **kwargs):
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        
        products = create_stock(validated_data=serializer.validated_data, company=request.user.company)
        output_serializer = ProductSerializer(products, many=True)
        
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

class ListVariantView(ModelViewSet):
    permission_classes = [IsAuthenticated, HasCompany]
    serializer_class = ProductSerializer
    
    def get_queryset(self):
        return Product.objects.filter(category__company=self.request.user.company).select_related('category').prefetch_related('variants')

class UpdateVariantView(ModelViewSet):
    permission_classes = [IsAuthenticated, HasCompany]
    serializer_class =  VariantUpdateSerializer
    
    def update(self, request, *args, **kwargs):
        print(f"Request data for update: {request.data}")
        id = self.kwargs.get('pk')
        try:
            variant = Variant.objects.get(id=id, product__category__company=request.user.company)
        except Variant.DoesNotExist:
            return Response({"detail": "Variant not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(
            variant,
            data=request.data,
            partial=True
        )
        print(f"Serializer instance: {serializer.instance}")
        serializer.is_valid(raise_exception=True)
        updated_variant(data=serializer.validated_data, instance=variant)        
        return Response({"detail": "Variant updated successfully."}, status=status.HTTP_200_OK)

        
        
        
    
        