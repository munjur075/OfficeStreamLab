import stripe
import uuid
import logging
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from accounts.models import User
from .models import Transaction


logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class CreateAddFundsCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        raw_amount = data.get("amount")
        payment_method = "stripe"

        # ------------------ Validate amount ------------------
        if not raw_amount:
            return Response({"message": "Required amount"}, status=400)

        try:
            amount = Decimal(raw_amount)
        except (InvalidOperation, TypeError):
            return Response({"message": "Invalid amount"}, status=400)

        if amount <= 0:
            return Response({"message": "Amount must be greater than zero"}, status=400)

        try:
            # ------------------ Create checkout session ------------------
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {"name": "Wallet Top-Up"},
                            "unit_amount": int(amount * 100),  # Stripe expects cents
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                # Prefer user_id for webhook identification
                metadata={
                    "user_id": str(request.user.id),
                    "amount": str(amount),
                    "payment_method": payment_method,
                    "email": request.user.email or "",
                },
                customer_email=request.user.email if request.user.email else None,
                success_url=request.build_absolute_uri(
                    reverse("subscription:stripe_add_funds_checkout_success")
                ) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=request.build_absolute_uri(
                    reverse("subscription:stripe_add_funds_checkout_cancel")+ f"?user_id={request.user.id}&amount={amount}"
                ),
            )

            logger.info(f"✅ Checkout session created for user={request.user.id}, amount={amount}")

            return Response(
                {
                    "sessionId": checkout_session.id,
                    "checkoutUrl": checkout_session.url,
                },
                status=200,
            )

        except Exception as e:
            logger.exception(f"❌ Error creating checkout session: {e}")
            return Response({"message": "Failed to create checkout session"}, status=500)


def stripe_add_funds_checkout_success_view(request):
    return JsonResponse({
        "status": "success",
        "message": "add_funds successfully."
    })

def stripe_add_funds_checkout_cancel_view(request):
    # Try to identify the user if possible (from session or query params)
    user_id = request.GET.get("user_id")
    amount = request.GET.get("amount", "0")

    # Generate unique subscription ID
    txn_cancle = f"cancle_{uuid.uuid4().hex[:12]}"
    user = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            user = None

    # if user:
    #     Transaction.objects.create(
    #         user=user,
    #         source="stripe",
    #         tx_type="fund",
    #         amount=Decimal(amount),
    #         txn_id=txn_cancle,
    #         balance_type="reelbux",
    #         status="failed",
    #         description=f"Wallet top-up cancelled by {user.email}"
    #     )

    return JsonResponse({
        "status": "cancelled",
        "message": "Add funds process was cancelled. You can try again anytime."
    })


