from django.urls import path
from .views import *

urlpatterns = [
    path('sign-up', SignupView.as_view(), name='sign_up'),
    
    # path('verify-email/', verify_otp, name='verify-email'),
    # path('resend-verification-code/', send_otp, name='resend-verification-code'),

    path('sign-in', SigninView.as_view(), name='sign_in'),
    path('admin-sign-in', AdminLoginView.as_view(), name='admin_sign_in'),

    path('forgo-password', RequestForgotPasswordView.as_view(), name='forgo_password'),
    path('verify-reset-code', VerifyResetCodeView.as_view(), name='verify_reset_code'),
    path('reset-password', ResetPasswordView.as_view(), name='reset_password'),

    path('change-password', ChangePasswordView.as_view(), name='change_password'),

    path('refresh', RefreshTokenView.as_view(), name='token_refresh'),

    path('get-user-profile', UserProfileView.as_view(), name='user_profile'),
]
