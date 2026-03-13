from django.shortcuts import render
from rest_framework import generics
from .serializers import *
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# Create your views here.
class RegisterView(generics.CreateAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
class UserDetailView(generics.RetrieveAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from tickets.paystack import get_banks
from .serializers import BankListSerializer, OnboardingSerializer


class BankListView(APIView):
    """
    GET /accounts/banks/
    Returns list of Nigerian banks from Paystack.
    Frontend calls this to populate the bank dropdown during onboarding.
    No auth required.
    """
    permission_classes = []

    def get(self, request):
        banks = get_banks()
        serializer = BankListSerializer(banks, many=True)
        return Response(serializer.data)


class OnboardingView(APIView):
    """
    POST /accounts/onboarding/
    Organizer submits their bank details.
    Creates a Paystack subaccount and stores the code on the user profile.
    Must be authenticated.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.paystack_subaccount_code:
            return Response(
                {"detail": "Bank account already registered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response(
            {"detail": "Bank account registered successfully."},
            status=status.HTTP_201_CREATED,
        )