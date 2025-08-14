from django.urls import path
from .views import *

urlpatterns = [
    path('sign-up/', SignupView.as_view(), name='sign-up'),
    
    # path('verify-email/', verify_otp, name='verify-email'),
    # path('resend-verification-code/', send_otp, name='resend-verification-code'),

    path('sign-in/', SigninView.as_view(), name='sign-in'),
    path('admin-sign-in/', AdminLoginView.as_view(), name='admin-sign-in'),

    path('forgo-password/', RequestForgotPasswordView.as_view(), name='forgo-password'),
    path('verify-reset-code/', VerifyResetCodeView.as_view(), name='verify-reset-code'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),

    path('change-password/', ChangePasswordView.as_view(), name='change-password'),

    path('refresh/', RefreshTokenView.as_view(), name='token_refresh'),

    path('get-user-profile/', UserProfileView.as_view(), name='user_profile'),
]
