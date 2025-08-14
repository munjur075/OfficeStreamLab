
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import User
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from django.utils import timezone
from .send_otp import send_otp
import random
import string
from datetime import timedelta
from django.contrib.auth.password_validation import validate_password
from .models import User, UserRole
import uuid


class SigninView(APIView):
    """
    Handle user login.
    """
    def post(self, request):
        email = request.data.get('email_address')
        password = request.data.get('password')

        if not email:
            return Response({"message": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"message": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, email=email, password=password)
        
        # return Response(user.role)
        if user is None:
            return Response({"message": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        return Response({
            "access_token": str(access_token),
            "refresh_token": str(refresh),
            "user_id": user.id,
        }, status=status.HTTP_200_OK)


class AdminLoginView(APIView):
    """
    Handle user login.
    """
    def post(self, request):
        email = request.data.get('email_address')
        password = request.data.get('password')

        if not email:
            return Response({"message": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"message": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(request, email=email, password=password)

        if user.is_superuser is False:
            return Response({"message": "You are not authorized to access this resource."}, status=status.HTTP_403_FORBIDDEN)

        if user is None:
            return Response({"message": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"message": "Your account is inactive."}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        return Response({
            "access_token": str(access_token),
            "refresh_token": str(refresh),
            "user_id": user.id,
        }, status=status.HTTP_200_OK)
    


class SignupView(APIView):
    """
    Handle user signup with optional referral code.
    """
    def post(self, request):
        full_name = request.data.get('full_name')
        email = request.data.get('email_address')
        password = request.data.get('password')
        confirm_password = request.data.get('confirm_password')
        distro_code = request.data.get('distro_code')  # Referral code
        terms_agreed = request.data.get('terms_agreed')

        # Validate required fields
        if not full_name:
            return Response({"message": "Full name is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not email:
            return Response({"message": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"message": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not confirm_password:
            return Response({"message": "Confirm password is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not terms_agreed:
            return Response({"message": "You must agree to the Terms of Service."}, status=status.HTTP_400_BAD_REQUEST)

        # Email exists check
        if User.objects.filter(email=email).exists():
            return Response({"message": "The email is already taken."}, status=status.HTTP_400_BAD_REQUEST)

        # Password match check
        if password != confirm_password:
            return Response({"message": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        # Password strength check
        try:
            validate_password(password)
        except Exception as e:
            return Response({"message": list(e)}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Use manager's create_user so distro_code 
        try:
            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name,
                terms_agreed=terms_agreed,
                distro_code=distro_code  # Pass referral code here
            )

            return Response({
                "id": user.id,
                "role": user.role,
                "distro_code": user.distro_code,
                "distro_by": user.distro_by.id if user.distro_by else None
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"message": f"Failed to create user. {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        

    
class RequestForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email_address')
        
        if not email:
            return Response({"message": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"message": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)

        otp = ''.join(random.choices(string.digits, k=6))
        try:
            user.otp = otp
            user.otp_expired = timezone.now() + timedelta(minutes=5)
            user.save()
            send_email = send_otp(email, otp)
        except Exception as e:
            return Response({"message": f"Failed to process OTP. {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if send_email:
            return Response({'user_id': user.id}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Failed to send OTP email. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyResetCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        otp = request.data.get('verification_code')

        if not user_id or not otp:
            return Response({"message": "Both User ID and verification code are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"message": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)

        if timezone.now() > user.otp_expired:
            return Response({"message": "verification code has expired."}, status=status.HTTP_400_BAD_REQUEST)

        if str(user.otp) == otp:
            secret_key = uuid.uuid4()
            user.reset_secret_key = secret_key
            user.save()
            return Response(
                {
                    "secret_key": str(secret_key)
                },
                status=status.HTTP_200_OK
            )

        return Response({"message": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        secret_key = request.data.get('secret_key')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        # Validate fields
        if not user_id or not secret_key or not new_password or not confirm_password:
            return Response(
                {"message": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {"message": "Passwords do not match."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(id=user_id, reset_secret_key=secret_key)
        except User.DoesNotExist:
            return Response(
                {"message": "Invalid secret key or user ID."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Set new password
        user.set_password(new_password)
        # user.reset_secret_key = None  # Invalidate the secret key
        # user.otp = None
        # user.otp_expired = None
        user.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        email = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not old_password or not new_password or not confirm_password:
            return Response(
                {"message": "Please provide all required password fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {"message": "New passwords do not match."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(email=email, password=old_password)
        print(email)
        if user is None:
            return Response(
                {"message": "Invalid old password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        refresh_token = request.data.get('refresh_token')

        if not refresh_token:
            return Response({'error': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            access_token = str(token.access_token)
            return Response({'access_token': access_token}, status=status.HTTP_200_OK)
        except TokenError as e:
            return Response({'error': 'Invalid or expired refresh token.'}, status=status.HTTP_401_UNAUTHORIZED)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({'data': serializer.data}, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)