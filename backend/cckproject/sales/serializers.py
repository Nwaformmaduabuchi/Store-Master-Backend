from rest_framework import serializers
from .models import Sale, SaleItem, StockMovement, Payment, Receipt, Customer, Refund
from products.models import Variant

class CustomerBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "customer_name",
            "customer_phone",
            "customer_address",
        ]

class SaleItemWriteSerializer(serializers.Serializer):
    """Used for INPUT — accepts variant_id, quantity, unit_price."""
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=Variant.objects.all(),
        source='variant'
    )
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
        
class UpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    sale_items = SaleItemWriteSerializer(many=True)

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'sale', 'amount_paid', 'payment_method', 'status', 'created_at']

class SaleItemReadSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    variant_size = serializers.CharField(source='variant.size', read_only=True)
    variant_color = serializers.CharField(source='variant.color', read_only=True)
    product_type = serializers.CharField(source='variant.product_type', read_only=True)
    remaining_amount = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()
    
    class Meta:
        model = SaleItem
        fields = [
            'id', 'variant_name', 'variant_size', 'product_type', 'variant_color',
            'quantity','product_name', 'unit_price', 'line_price', 'item_status', 'remaining_amount', "payments"
        ]

    def get_payments(self, obj):
        return obj.payments

    def get_remaining_amount(self, obj):
        return obj.remaining_amount

class SaleSerializer(serializers.ModelSerializer):
    
    sale_items = SaleItemReadSerializer(many=True, read_only=True)
    outstanding_amount = serializers.SerializerMethodField()
    customer = CustomerBasicSerializer(read_only=True)

    class Meta:
        model = Sale
        fields = [
            'id',
            'customer', 
            'sale_status', 
            'seller',
            'created_at',
            'updated_at',
            'total_amount',
            'outstanding_amount',
            'sale_items', 
        ]

    def get_outstanding_amount(self, obj):
        return obj.outstanding_amount

class CustomerSerializer(serializers.ModelSerializer):
    sales = SaleSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "customer_name",
            "customer_phone",
            "customer_address",
            "sales",
            "company",
        ]

class CreateSaleSerializer(serializers.Serializer):
    """Input serializer for creating a sale."""
    customer_name = serializers.CharField(max_length=255)
    customer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    customer_address = serializers.CharField(required=False, allow_blank=True)
    seller = serializers.CharField(max_length=255, required=False, allow_blank=True)
    sale_items = SaleItemWriteSerializer(many=True)

class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ['id',
                   'variant', 
                   'sale_item', 
                   'sale', 'payment', 
                   'quantity_change', 
                   'movement_type', 
                   'note', 
                   'created_at']

class PaymentInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    method = serializers.ChoiceField(choices=Payment.PaymentChoices.choices, required=False)

class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ['id',
                  'receipt_no',
                  'payment',
                  'sale' 
                  'created_at']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "sale",
            "status",
            "amount_paid",
            "payment_method",
            "created_at",
        ]
class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = [
            "id",
            "amount",
            "sale",
            "created_at",
        ]

class SaleWithPaymentsSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)
    refunds = RefundSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = [
            "id",
            "total_amount",
            "total_payment",
            "outstanding_amount",
            "sale_status",
            "payments",
            "refunds",
        ]


