from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError, APIException
from .models import Company

User = get_user_model()


def create_user(*, data):
    if not data or not isinstance(data, dict):
        raise ValidationError("Valid user data must be provided as a dictionary.")
        
    try:
        return User.objects.create_user(**data)
    except IntegrityError:
        raise ValidationError("A user with these unique details already exists.")
    except Exception as e:
        # Catch unexpected errors to prevent 500 server crashes
        raise APIException(f"An unexpected error occurred while creating the user: {str(e)}")


class CompanyService:
    @staticmethod
    def create_company(*, data, owner):
        print("inside service ...", getattr(owner, 'has_company', False))
        
        if not owner:
            raise ValidationError("An owner must be provided to register a company.")
            
        if not data or not isinstance(data, dict):
            raise ValidationError("Valid company data must be provided.")

        try:
            company, created = Company.objects.get_or_create(
                owner=owner,
                defaults={
                    **data
                }
            )
            
            if not created:
                raise ValidationError('Company already exists for this owner.')
                
            owner.has_company = True
            owner.save(update_fields=["has_company"])
            return company
            
        except ValidationError:
            # Re-raise the ValidationError so DRF can return a 400 response
            raise
        except IntegrityError:
            raise ValidationError("A database integrity error occurred. Ensure unique fields are not duplicated.")
        except Exception as e:
            # Original print statement preserved for your debugging
            print(e)
            raise APIException("An unexpected error occurred while setting up the company.")