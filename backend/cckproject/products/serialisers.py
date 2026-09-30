from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Product, Variant, Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "company"]

class CategoryInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)

class VariantSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name")
    class Meta:
        model = Variant
        fields = ["id","name", "color", "size", "quantity", "price","product_type","product_name"  ]

class VariantUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = ["id","name", "color", "size", "quantity","product_type", "price"]

class VariantInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    color = serializers.CharField(allow_blank=True, required=False)
    size = serializers.CharField(allow_blank=True, required=False)
    product_type = serializers.CharField(allow_blank=True, required=False)
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    variants = VariantSerializer(many=True)
    class Meta:
        model = Product
        fields = ["id", "name", "description", "category", "variants"]
            
            

class ProductInputSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    variants = VariantInputSerializer(many=True)

class CreateStockSerializer(serializers.Serializer):
    category = CategoryInputSerializer()
    products = ProductInputSerializer(many=True)
