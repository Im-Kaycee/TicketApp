from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
 
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    token = serializers.SerializerMethodField()


    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password','password2', 'token']
    def get_token(self, obj):
        refresh = RefreshToken.for_user(obj)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        try:
            validate_password(data['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        
        return data
    def create(self, validated_data):
        user = get_user_model().objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password']
        )
        return user        
from django.contrib.auth import authenticate

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_new_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({"new_password": "New passwords must match."})
        return data

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value


from tickets.paystack import get_banks, create_subaccount
from rest_framework import serializers
from .models import User


class BankListSerializer(serializers.Serializer):
    """
    Serializes the bank list returned from Paystack.
    Used to populate the bank dropdown on the frontend.
    """
    name = serializers.CharField()
    code = serializers.CharField()


class OnboardingSerializer(serializers.Serializer):
    """
    Accepts the organizer's bank details during onboarding.
    Calls Paystack to create a subaccount and stores the code on the user.
    """
    account_number = serializers.CharField(max_length=10)
    bank_code = serializers.CharField(max_length=10)
    bank_name = serializers.CharField(max_length=100)

    def save(self, user):
        validated = self.validated_data

        subaccount_code = create_subaccount(
            business_name=user.get_full_name() or user.username,
            bank_code=validated["bank_code"],
            account_number=validated["account_number"],
            percentage_charge=95.00,  # organizer gets 95%, you keep 5%
        )

        user.paystack_subaccount_code = subaccount_code
        user.account_number = validated["account_number"]
        user.bank_name = validated["bank_name"]
        user.save(update_fields=[
            "paystack_subaccount_code",
            "account_number",
            "bank_name",
        ])

        return user