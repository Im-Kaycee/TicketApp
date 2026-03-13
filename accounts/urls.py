from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import *

urlpatterns = [
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name = 'register'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path("banks/", BankListView.as_view(), name="bank-list"),
    path("onboarding/", OnboardingView.as_view(), name="onboarding"),
]