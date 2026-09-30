from django.db import models
from django.contrib.auth.models import AbstractUser
from .manager import UserManager
import uuid



# Create your models here.

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    username = None
    email = models.EmailField(unique=True)
    has_company = models.BooleanField(default=False)
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class Company(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    owner = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="company",
    )

    name = models.CharField(max_length=255, unique=True, default="")

    email = models.EmailField(max_length=255, blank=True, null=True)

    phone = models.CharField(max_length=20, blank=True, null=True)

    location = models.CharField(max_length=255)

    logo = models.ImageField(
        upload_to="logos/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering=["created_at"]
    def __str__(self):
        return self.name


