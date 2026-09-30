from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Company, User

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "location",
            "logo",
            "created_at",
        ]

class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["admin"] = "cck"
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        data["has_company"] = self.user.has_company
        return data
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "has_company",
            
                ]

class UserDataSerializer (serializers.Serializer):
    user = UserSerializer()
    company = CompanySerializer()
