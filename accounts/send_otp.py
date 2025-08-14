from django.core.mail import send_mail
from django.conf import settings

def send_otp(email, otp):
    subject = "Your OTP Code"
    message = f"Your OTP code is {otp}. It will expire in 5 minutes."
    print(otp)
    from_email = settings.EMAIL_HOST_USER
    try:
        send_mail(subject, message, from_email, [email])
        return True
    except Exception as e:
        print(f"Send OTP Error: {e}")
        return False
