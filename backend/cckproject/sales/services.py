from django.db import transaction
from django.db.models import Sum, F
from rest_framework.exceptions import ValidationError, NotFound
from decimal import Decimal

from .models import Sale, SaleItem, StockMovement, Customer, Payment, PaymentAllocation, Receipt, Refund, NoPaymentReceipt
from products.models import Variant
from myproject.utils import ManageStock


class SaleService:
    @staticmethod
    @transaction.atomic
    def create_sale(*, data, company):
        sale_items_data = data.get('sale_items')

        if not sale_items_data or not isinstance(sale_items_data, list):
            raise ValidationError({"sale_items": "Sale must contain at least one valid item in a list format."})

        unique_items = []
        seen = set()
        
        for item in sale_items_data:
            if 'variant' not in item or 'quantity' not in item or 'unit_price' not in item:
                raise ValidationError("Each sale item must include 'variant', 'quantity', and 'unit_price'.")
            
            if item['quantity'] <= 0:
                raise ValidationError(f"Quantity must be greater than zero for variant {item['variant'].pk}.")
            if item['unit_price'] < 0:
                raise ValidationError(f"Unit price cannot be negative for variant {item['variant'].pk}.")

            variant_id = item['variant'].pk
            if variant_id not in seen:
                seen.add(variant_id)
                unique_items.append(item)

        if not data.get('customer_name'):
            raise ValidationError({"customer_name": "Customer name is required."})

        customer, _ = Customer.objects.get_or_create(
            customer_name=data['customer_name'],
            company=company,
            defaults={
                'customer_phone': data.get('customer_phone', ''),
                'customer_address': data.get('customer_address', '')
            }
        )

        sale = Sale.objects.create(customer=customer, company=company, seller=data.get('seller', ''))
        total = Decimal('0.00')

        variant_ids = sorted(set(item['variant'].pk for item in unique_items))

        locked_variants = {
            v.pk: v for v in Variant.objects
                .select_related('product')
                .select_for_update()
                .filter(pk__in=variant_ids, product__category__company=company)
        }

        if len(locked_variants) != len(variant_ids):
            missing = set(variant_ids) - set(locked_variants.keys())
            raise ValidationError(f"One or more variants were not found or do not belong to the company: {missing}")

        for item_data in unique_items:
            variant = locked_variants[item_data['variant'].pk]
            quantity = item_data['quantity']
            unit_price = item_data['unit_price']
            line_price = quantity * unit_price

            if quantity > variant.quantity:
                raise ValidationError(f"Insufficient stock for '{variant.name}'. Requested: {quantity}, Available: {variant.quantity}")

            ManageStock.reduce_stock(variant, quantity)
            sale_item = SaleItem.objects.create(
                sale=sale,
                variant=variant,
                quantity=quantity,
                unit_price=unit_price,
                line_price=line_price
            )

            total += sale_item.line_price

            StockMovement.objects.create(
                variant=variant,
                sale=sale,
                quantity_change=-quantity,
                movement_type=StockMovement.MovementType.SALE,
                note=f"Sold {quantity} unit(s) of {variant.name}"
            )

        sale.total_amount = total
        sale.save(update_fields=['total_amount'])
        return sale
    
    @staticmethod
    @transaction.atomic
    def delete_item(*, item_id):
        if not item_id:
            raise ValidationError({"item_id": "Item ID is required to perform deletion."})

        try:
            sale_item = (
                SaleItem.objects
                .select_for_update()
                .select_related("sale", "variant")
                .get(pk=item_id)
            )
                
            sale = sale_item.sale
                
            ManageStock.add_stock(sale_item.variant, sale_item.quantity)
            
            StockMovement.objects.create(
                variant=sale_item.variant,
                sale=sale,
                sale_item=sale_item,
                quantity_change=sale_item.quantity,
                movement_type=StockMovement.MovementType.CANCEL,
                note=f"Restocked {sale_item.quantity} unit(s) of {sale_item.variant.name} (Sale item cancelled)"
            )
            
            sale_item.delete()

            sale.total_amount = sale.sale_items.aggregate(
                total=Sum(F('line_price'))
            )['total'] or Decimal('0.00')
                
            sale.save(update_fields=["total_amount"])
            return sale
                
        except SaleItem.DoesNotExist:
            raise NotFound("Sale item does not exist.")

    # Update service
    @staticmethod
    @transaction.atomic
    def partial_update(*, instance, data):
        if not data:
            raise ValidationError("No valid data provided for update.")

        variant = instance.variant
        delta = 0

        if 'quantity' in data:
            new_quantity = data['quantity']
            
            if new_quantity <= 0:
                raise ValidationError({"quantity": "Quantity must be greater than zero."})
                
            old_quantity = instance.quantity
            delta = new_quantity - old_quantity

            if delta > 0:
                if delta > variant.quantity:
                    raise ValidationError(
                        f"Insufficient stock for '{variant.name}'. Short by {delta - variant.quantity} unit(s)."
                    )

                ManageStock.reduce_stock(variant, delta)

            elif delta < 0:
                ManageStock.add_stock(variant, -delta)

        if 'unit_price' in data and data['unit_price'] < 0:
            raise ValidationError({"unit_price": "Unit price cannot be negative."})

        quantity = data.get('quantity', instance.quantity)
        price = data.get('unit_price', instance.unit_price)

        for attr, value in data.items():
            setattr(instance, attr, value)

        instance.line_price = quantity * price

        instance.save(
            update_fields=list(set(data.keys()) | {"line_price"})
        )

        sale = instance.sale

        sale.total_amount = (
            sale.sale_items
            .select_for_update()
            .aggregate(total=Sum('line_price'))['total']
            or Decimal('0.00')
        )

        sale.save(update_fields=['total_amount'])

        if delta != 0:
            StockMovement.objects.create(
                variant=variant,
                sale_item=instance,
                sale=sale,
                quantity_change=-delta,
                movement_type=StockMovement.MovementType.UPDATE,
                note=f"Adjusted {variant.name} stock by {-delta} (Sale item updated)"
            )

        return instance

    # full update
    @staticmethod
    @transaction.atomic
    def full_create(*, data, company):
        new_items = data.get('sale_items')
        
        if not new_items or not isinstance(new_items, list):
            raise ValidationError({"sale_items": "A list of new sale items is required."})

        if 'id' not in data:
            raise ValidationError({"id": "Sale ID is required."})

        try:
            sale = Sale.objects.get(pk=data['id'], company=company)
        except Sale.DoesNotExist:
            raise NotFound("Sale not found.")
            
        total = sale.total_amount 
        existing_item = sorted(set(list(sale.sale_items.values_list('variant_id', flat=True)))) 

        seen = []                  

        for d in new_items:
            if 'variant' not in d or 'quantity' not in d or 'unit_price' not in d:
                raise ValidationError("Each new item must include 'variant', 'quantity', and 'unit_price'.")
                
            if d['quantity'] <= 0:
                raise ValidationError("Quantity must be greater than zero.")
            if d['unit_price'] < 0:
                raise ValidationError("Unit price cannot be negative.")

            variant_id = d['variant'].pk
            if variant_id in existing_item:
                raise ValidationError(f"Product '{d['variant'].name}' already exists in this sale.")
            
            if variant_id in seen:
                raise ValidationError(f"Product '{d['variant'].name}' already exists in the request.")
            seen.append(variant_id)
            
            if d['quantity'] > d['variant'].quantity:
                raise ValidationError(f"Insufficient stock for '{d['variant'].name}'.")
                
            sale_item = sale.sale_items.create(
                variant=d['variant'],
                quantity=d['quantity'],
                unit_price=d['unit_price'],
                line_price=d['quantity'] * d['unit_price']
            )

            ManageStock.reduce_stock(d['variant'], d['quantity'])

            StockMovement.objects.create(
                variant=d['variant'],
                sale=sale,
                quantity_change=-d['quantity'],
                movement_type=StockMovement.MovementType.SALE,
                note=f"Sold {d['quantity']} unit(s) of {d['variant'].name} (Added to existing sale)"
            )
            total += sale_item.line_price

        sale.total_amount = total
        sale.save(update_fields=['total_amount'])
        return sale

    
    @staticmethod
    @transaction.atomic
    def complete_payment(*, data, instance, key=None):
        if 'amount' not in data or 'method' not in data:
            raise ValidationError("Both 'amount' and 'method' are required to process a payment.")

        print("payment started")
        if data["amount"] < 0:
            return SaleService.refund_payment(data["amount"], instance)
            
        if data["amount"] == 0:
            return  
            
        existing_payment = Payment.objects.filter(idempotency_key=key).first()
        if existing_payment:
            return existing_payment
        
        payment = Payment.objects.create(
            idempotency_key=key,
            sale=instance,
            amount_paid=data["amount"],
            payment_method=data['method'],
        )
        
        StockMovement.objects.create(
            sale=instance,
            movement_type=StockMovement.MovementType.PAYMENT,
            note=f"Payment of {data['amount']} logged against Sale #{instance.id}"
        )
        
        amount = payment.amount_paid
        sale_items = instance.sale_items.select_for_update()
        
        for item in sale_items:
            item_paid = item.allocations.aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0.00")

            remaining = item.line_price - item_paid
            if remaining <= 0:
                continue  
                
            allocation = min(amount, remaining)
            if allocation == 0:
                break
                
            amount -= allocation
            PaymentAllocation.objects.create(
                payment=payment,
                sale_item=item,
                amount=allocation
            )
        
            total_paid = item_paid + allocation
            if total_paid >= item.line_price:
                item.item_status = "completed"
            elif total_paid < item.line_price:
                item.item_status = "partial"
                
            item.save(update_fields=["item_status"])
            
        if instance.outstanding_amount == 0:
            instance.sale_status = "completed"
            ReceiptCreateService.generate_receipt(sale=instance,payment=payment, key=key)
        else:
            instance.sale_status = "partial"
            
        instance.save(update_fields=["sale_status"])
        return payment
    
    @staticmethod
    @transaction.atomic
    def refund_payment(amount, instance):
        if amount >= 0:
             raise ValidationError("Refund amount passed to the handler must be a negative value.")
             
        payment = instance.payments.first()
        total_payment = instance.payments.first()
        
        if not payment or not total_payment:
            raise ValidationError("No payment found to refund for this sale.")
            
        total_payment.amount_paid += amount
        total_payment.save(update_fields=["amount_paid"])

        allocation = payment.allocations.first()

        if not allocation:
            raise ValidationError("No payment allocation found to apply refund.")

        new_amount = allocation.amount + amount

        if new_amount < 0:
            raise ValidationError("Refund requested exceeds the allocated payment.")

        allocation.amount = new_amount
        allocation.save(update_fields=["amount"])
       
        Refund.objects.create(
            amount=abs(amount),
            sale=instance
        )
        
        # Checking if REFUND exists in MovementType, otherwise fallback to standard Payment note format.
        m_type = getattr(StockMovement.MovementType, 'REFUND', StockMovement.MovementType.PAYMENT)
        StockMovement.objects.create(
            sale=instance,
            movement_type=m_type,
            note=f"Refund of {abs(amount)} processed for Sale #{instance.id}"
        )
       
        instance.sale_status = "completed"
        instance.save(update_fields=["sale_status"])
        
        return total_payment

    
    @staticmethod
    @transaction.atomic
    def view_payment(*, sale_id):
        if not sale_id:
            raise ValidationError({"sale_id": "Sale ID is required to retrieve payments."})
            
        try:
            sale = Sale.objects.get(pk=sale_id)
        except Sale.DoesNotExist:
            raise NotFound("Sale not found.")
            
        payments = sale.payments.all()
        return payments


class ReceiptCreateService:
    @staticmethod
    @transaction.atomic
    def generate_receipt(*, sale, payment, key):
        print('service for no payment receipt enterd')
        if not payment:
            print('service for no payment receipt enterd')
        
        if not sale:
            raise ValidationError("Both sale and payment instances are required to generate a receipt.")
            
        company = sale.company

        try:
            return payment.receipt
        except Receipt.DoesNotExist:
            pass
        
        existing_receipt = Receipt.objects.filter(idempotency_key=key).first()
        
        if existing_receipt is not None:
            return existing_receipt
            
        name = company.name.split()[0] if company.name else ""
        number = f"{sale.id:02d}-{payment.id:03d}"
        
        receipt = Receipt.objects.create(
            sale=sale,
            idempotency_key=key,
            payment=payment,
            receipt_no=f"{name}-{number}" 
        )
        return receipt

    def generate_no_payment_receipt(*, sale, key):
            print('service for no payment receipt enterd')
            if not sale :
                raise ValidationError("Both sale and payment instances are required to generate a receipt.")
                
            company = sale.company
            
            existing_receipt = NoPaymentReceipt.objects.filter(idempotency_key=key).first()
            
            if existing_receipt is not None:
                return existing_receipt
                
            name = company.name.split()[0] if company.name else ""
            number = f"{sale.id:02d}"
            
            receipt = NoPaymentReceipt.objects.create(
                sale=sale,
                idempotency_key=key,
                receipt_no=f"{name}-{number}" 
            )
            return receipt