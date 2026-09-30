import logging
from decimal import Decimal

from django.db import transaction, IntegrityError, DatabaseError
from django.db.models import ProtectedError
from rest_framework.exceptions import APIException, ValidationError

from myproject.utils import ManageStock
from sales.models import StockMovement
from .models import Product, Variant, Category


logger = logging.getLogger(__name__)

@transaction.atomic
def create_stock(*, validated_data, company):
    logger.info(f"Creating stock for company: {company.id if hasattr(company, 'id') else company}")

    if not validated_data or not isinstance(validated_data, dict):
        raise ValidationError("Invalid payload format. Expected a dictionary.")

    variant_name = Variant.objects.all().values_list('name', flat=True)
   
    try:
        category_data = validated_data["category"]
        product_data = validated_data["products"]
    except KeyError as e:
        raise ValidationError(f"Missing required payload field: {e}")

    if not category_data.get("name"):
        raise ValidationError({"category": "Category name is required."})

    if not isinstance(product_data, list):
        raise ValidationError({"products": "Products must be provided as a list."})
    
    try:
        category, _ = Category.objects.get_or_create(
            name=category_data["name"],
            company=company
        )
        logger.debug(f"Category created/fetched: {category}")
    except DatabaseError as e:
        logger.exception("Database error while creating category")
        raise APIException("Failed to process category")

    products = []

    for product in product_data:
        if "name" not in product:
            raise ValidationError("Each product must have a 'name'.")

        try:
            variants_data = product["variants"]
        except KeyError:
            raise ValidationError(f"No Variants provided for product '{product.get('name')}'")
            
        if not isinstance(variants_data, list):
            raise ValidationError(f"'variants' for product '{product.get('name')}' must be a list.")
        
        try:
            product_instance, _ = Product.objects.get_or_create(
                name=product["name"],
                category=category,
                defaults={
                    "description": product.get("description", "")
                }
            )
            logger.debug(f"Product created/fetched: {product_instance}")
        except IntegrityError as e:
            logger.error(f"Error creating product '{product.get('name')}'")
            raise ValidationError(f"Error creating product '{product.get('name')}'")
        except Exception as e:
            logger.exception(f"Unexpected error creating product '{product.get('name')}'")
            raise APIException("An unexpected error occurred while creating a product.")
        
        for variant in variants_data:
            try:
                variant_quantity = int(variant.get("quantity", 0))
                variant_price = Decimal(variant.get("price", "0.00"))

                if variant_quantity < 0:
                    raise ValidationError(f"Quantity cannot be negative for variant '{variant.get('name', 'Unknown')}'.")
                if variant_price < 0:
                    raise ValidationError(f"Price cannot be negative for variant '{variant.get('name', 'Unknown')}'.")

                variant_instance, created = Variant.objects.get_or_create(
                    product=product_instance,
                    name=variant.get("name", ""),
                    color=variant.get("color"),
                    size=variant.get("size"),
                    product_type=variant.get("product_type"),
                    defaults={
                        "quantity": variant_quantity,
                        "price": variant_price
                    }
                )
                
                if created:
                    if variant_quantity > 0:
                        StockMovement.objects.create(
                            variant=variant_instance,
                            movement_type="receive",
                            quantity_change=variant_quantity,
                            note=f"Initial stock of {variant_quantity} unit(s) added"
                        )
                else:   
                    if variant_quantity > 0:
                        ManageStock.add_stock(variant_instance, variant_quantity)
                        StockMovement.objects.create(
                            variant=variant_instance,
                            movement_type="receive",
                            quantity_change=variant_quantity,
                            note=f"Restocked {variant_quantity} unit(s)",
                        )
                        logger.debug(f"Stock movement created for variant: {variant_instance.id}")
                    
                    if "price" in variant:
                        variant_instance.price = variant_price
                        variant_instance.save(update_fields=["price"])

            except IntegrityError as e:
                logger.error(f"IntegrityError processing variant for product '{product_instance.name}': {e}")
                raise ValidationError("Check for missing or duplicate fields in variant data.")
            except ValueError:
                raise ValidationError("Invalid number format for price or quantity.")
            except Exception as e:
                logger.exception(f"Error processing variant for product '{product_instance.name}'")
                raise APIException("An error occurred while processing product variants.")

        products.append(product_instance)
    
    return products


@transaction.atomic
def delete_variant(*, variant):
    if not variant:
        raise ValidationError("A valid variant must be provided for deletion.")
        
    try:
        # Log the stock removal before the variant is deleted
        if variant.quantity > 0:
            StockMovement.objects.create(
                variant=variant,
                movement_type="remove",
                quantity_change=-variant.quantity,
                note=f"Removed {variant.quantity} unit(s) (Variant deleted)"
            )
            
        variant.delete()
    except ProtectedError as e:
        # Raised if a foreign key is preventing deletion (e.g., Variant is attached to past Orders)
        logger.warning(f"Attempted to delete protected variant {variant.id}: {e}")
        raise ValidationError("Sorry, this item cannot be deleted as it is linked to existing records.")
        
    except Exception as e:
        logger.exception(f"Error deleting variant {variant.id if variant else 'None'}")
        raise APIException("An unexpected error occurred!")

@transaction.atomic
def updated_variant(*, data, instance):
    if not data or not isinstance(data, dict):
        raise ValidationError("Valid update data must be provided.")

    try:
        delta = 0
        if "quantity" in data:
            new_quantity = int(data["quantity"])
            if new_quantity < 0:
                raise ValidationError({"quantity": "Quantity cannot be set to a negative value."})
            
            old_quantity = instance.quantity
            delta = new_quantity - old_quantity

        if "price" in data and Decimal(data["price"]) < 0:
            raise ValidationError({"price": "Price cannot be set to a negative value."})

        for attr, value in data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if delta != 0:
            action = "increased" if delta > 0 else "decreased"
            StockMovement.objects.create(
                variant=instance,
                movement_type="adjustment",
                quantity_change=delta,
                note=f"Stock {action} by {abs(delta)} unit(s) (Manual update)"
            )

        logger.info(f"Variant {instance.id} updated successfully.")
    except ValueError:
        raise ValidationError("Invalid number format provided for quantity or price.")
    except IntegrityError as e:
        logger.error(f"IntegrityError updating variant {instance.id}: {e}")
        raise ValidationError("A unique constraint error occurred. Please check your data.")
    except Exception as e:
        logger.exception(f"Unexpected error updating variant {instance.id}")
        raise APIException("An unexpected error occurred!")