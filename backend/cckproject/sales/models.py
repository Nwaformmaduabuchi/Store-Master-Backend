from django.db import models
from decimal import Decimal
from django.db.models import Sum
import uuid
from users.models import Company
from rest_framework.exceptions import ValidationError

# Create your models here.

class Customer(models.Model):
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)
    company = models.ForeignKey(
                Company,
                on_delete=models.CASCADE,
                related_name="customers",
                null=True,
                blank=True
            )


class Sale(models.Model):

    class SaleStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partial"
        CANCELED = "canceled", "Canceled"


    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="sales")

    company = models.ForeignKey(
            Company,
            on_delete=models.CASCADE,
            related_name="sales",
                null=True,
                blank=True
        )
    sale_status = models.CharField(max_length=20, choices=SaleStatus.choices, default=SaleStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    seller = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ["-updated_at"]
    @property
    def outstanding_amount(self):
        total_paid = self.payments.aggregate(total=Sum('allocations__amount'))['total'] or Decimal('0.00')
        total =  self.total_amount - total_paid
        # if total < 0:
        #     print('cannot be refunded')
        #     raise ValidationError("cannot be refunded")
        return total
        
    @property
    def total_payment(self):
        total_paid = self.payments.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
        return total_paid

    def __str__(self):
        return f"Sale #{self.id} - {self.customer.customer_name} - {self.sale_status}"

class SaleItem(models.Model):
    class  ItemStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partial"
        RETURNED = "returned", "Returned"
        
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="sale_items")
    variant = models.ForeignKey("products.Variant", on_delete=models.PROTECT, related_name="sale_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2) 
    line_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    item_status = models.CharField(max_length=20, choices=ItemStatus.choices, default=ItemStatus.PENDING)


    
    @property
    def remaining_amount(self):
        return self.line_price
    @property
    def payments(self):
        return list(self.allocations.values_list("amount", flat=True))

    def __str__(self):
        return f"{self.sale.customer.customer_name} - {self.variant.product.name} ({self.variant.color}, {self.variant.size})"

class Payment(models.Model):

    class PaymentChoices(models.TextChoices):
        CASH = "cash", "Cash"
        DEBIT_CARD = "debit_card", "Debit Card"
        TRANSFER = "transfer", "Transfer"
        OTHER = "other", "Other"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partial"

    idempotency_key = models.UUIDField(default=uuid.uuid4, editable=False,unique=True)
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="payments")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentChoices.choices, default=PaymentChoices.CASH)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]


    def __str__(self):
        return f"Payment of {self.amount_paid} for Sale #{self.sale.id} via {self.payment_method}"

class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        SALE = "sale", "Sale"
        RETURN = "return", "Return"
        CANCEL = "cancel", "Cancel"
        DAMAGED = "damaged", "Damaged"
        RECEIVE = "receive", "Receive"
        UPDATE = "update", "Update"
        PAYMENT = "payment", "Payment"

    variant = models.ForeignKey("products.Variant", on_delete=models.SET_NULL, related_name="stock_movements", null=True, blank=True)
    sale = models.ForeignKey(Sale, on_delete=models.SET_NULL, related_name="stock_movements", null=True, blank=True)
    sale_item = models.ForeignKey(SaleItem, on_delete=models.SET_NULL, related_name="stock_movements", null=True, blank=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, related_name="stock_movements", null=True, blank=True)
    quantity_change = models.IntegerField(blank=True, null=True)
    movement_type = models.CharField(max_length=50, choices=MovementType.choices)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        ordering=["-created_at"]

    def __str__(self):
        return f"{self.movement_type} - {self.variant.product.name} ({self.variant.color}, {self.variant.size}) - {self.quantity_change}"


class Receipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.UUIDField(default=uuid.uuid4, editable=False,unique=True)
    receipt_no = models.CharField(max_length=50, unique=True, default="") 
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name="receipt", null=True, blank=True)
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="receipts", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    @property
    def total_payments(self):
        return self.sale.payments.aggregate(
            total=Sum("amount_paid")
        )["total"] or Decimal("0.00")

    class Meta:
        ordering=["-created_at"]

    def __str__(self):
        return f"Receipt for Sale #{self.payment.id or None}"

class PaymentAllocation(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="allocations")
    sale_item = models.ForeignKey(SaleItem, on_delete=models.CASCADE, related_name="allocations")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['payment', 'sale_item'], name='unique_payment_allocation')
        ]
        ordering = ["-created_at"]

class Refund(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="refunds")

    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Refund for order_no:{self.sale.id or None}"



class NoPaymentReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.UUIDField(default=uuid.uuid4, editable=False,unique=True)
    receipt_no = models.CharField(max_length=50, unique=True, default="")
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="no_pay_receipts", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    @property
    def total_payments(self):
        return self.sale.payments.aggregate(
            total=Sum("amount_paid")
        )["total"] or Decimal("0.00")

    class Meta:
        ordering=["-created_at"]

    def __str__(self):
        return f"Receipt for Sale #{self.sale.id or None}"