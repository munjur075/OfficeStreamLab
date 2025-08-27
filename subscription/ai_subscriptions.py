import uuid
from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from accounts.models import User
from .models import UserSubscription, SubscriptionPlan, Wallet

class CreateReelBuxCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user

        # Check active subscription
        if UserSubscription.objects.filter(user=user, status="active").exists():
            return Response(
                {"message": "You already have an active subscription."},
                status=status.HTTP_200_OK
            )

        # Get data
        data = request.data
        plan_name = data.get("plan", "Basic")
        duration_days = int(data.get("duration_days", 30))
        limit_value = int(data.get("limit_value", 0))

        # Get plan
        plan = SubscriptionPlan.objects.filter(name=plan_name).first()
        if not plan:
            return Response({"error": "Invalid plan"}, status=status.HTTP_400_BAD_REQUEST)

        subscription_price = plan.price

        # Get wallet
        wallet = getattr(user, "wallet", None)
        if not wallet:
            return Response({"error": "Wallet not found"}, status=status.HTTP_400_BAD_REQUEST)

        # Check balance
        if wallet.reel_bux_balance < subscription_price:
            return Response({"error": "Insufficient ReelBux balance"}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct balance
        wallet.reel_bux_balance -= subscription_price
        wallet.save()

        # Create subscription
        subscription = UserSubscription.objects.create(
            user=user,
            plan_name=plan_name,
            payment_method="reelbux",
            subscription_id=f"reelbux_{uuid.uuid4().hex[:16]}",  # custom ID
            price=subscription_price,
            limit_value=limit_value,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=duration_days),
            cancel_at_period_end=False,
            payment_status="completed",
            status="active",
        )

        # ✅ Mark user as subscribed
        user.is_subscribe = True
        user.save()


        return Response({
            "message": "Subscription activated using ReelBux balance.",
            "subscription_id": subscription.subscription_id,
            "new_balance": wallet.reel_bux_balance
        }, status=status.HTTP_201_CREATED)
