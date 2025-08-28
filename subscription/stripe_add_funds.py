import stripe
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from .models import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

stripe.api_key = settings.STRIPE_SECRET_KEY

class CreateAddFundsCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        data = request.data
        amount = data.get("amount")
        # payment_method = data.get("payment_method")
        payment_method = "stripe"
        
        if not amount:
            return Response({"message": "Required amount"}, status=400)
        # if not payment_method:
        #     return Response({"message": "Select payment method"}, status=400)

        try:
            checkout_session = stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Wallet Top-Up"},
                        "unit_amount": int(float(amount) * 100),  # Stripe expects cents
                    },
                    "quantity": 1,
                }],
                customer_email=request.user.email,
                metadata={
                    "user_id": str(request.user.id),
                    "amount": amount,
                    "payment_method": str(payment_method)
                },
                success_url=request.build_absolute_uri(reverse("subscription:stripe_add_funds_checkout_success")) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=request.build_absolute_uri(reverse("subscription:stripe_add_funds_checkout_cancel")),
            )

            # print(session)
        except Exception as e:
            return Response({"message": str(e)}, status=500)

        return Response({
        "sessionId": checkout_session.id,
        "checkoutUrl": checkout_session.url
    })

def stripe_add_funds_checkout_success_view(request):
    return JsonResponse({
        "status": "success",
        "message": "Subscription successful! You can now access premium features."
    })

def stripe_add_funds_checkout_cancel_view(request):
    return JsonResponse({
        "status": "cancelled",
        "message": "Subscription process was cancelled. You can try again anytime."
    })


