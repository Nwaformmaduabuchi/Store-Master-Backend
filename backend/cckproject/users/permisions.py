from rest_framework.permissions import BasePermission


class HasCompany(BasePermission):
    
    def has_permission(self, request, view):
        message = "COMPANY REQUIRED: User is required to register a company"
        if not request.user or not request.auth:
           return False

        if not getattr(request.user,"has_company", False):
            return False
        
        return True