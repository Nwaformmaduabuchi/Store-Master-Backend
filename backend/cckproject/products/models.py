from django.db import models
from django.conf import settings
from users.models import Company

# Create your models here.

from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="categories")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "company"],
                name="unique_category_per_company"
            )
        ]
        ordering=["created_at"]


    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "category"],
                name="unique_product_per_category"
            )
        ]
        ordering=["created_at"]

    def __str__(self):
        return self.name


class Variant(models.Model):
    name = models.CharField(max_length=100, default="")
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants"
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    product_type = models.CharField(max_length=100, default="",
        blank=True)
    color = models.CharField(max_length=50,default="",
        blank=True )
    size = models.CharField(max_length=50, default="",
        blank=True)
    quantity = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product","color", "size","product_type","name"],
                name="unique_product_variant"
            )
        ]

        ordering=["created_at"]

    def __str__(self):
        return f"{self.name}"