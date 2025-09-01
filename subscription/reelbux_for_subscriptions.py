import uuid
from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from accounts.models import User
from .models import UserSubscription, SubscriptionPlan, Wallet, Transaction


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

        # Get request data
        data = request.data
        plan_name = data.get("plan", "Basic")
        duration_days = int(data.get("duration_days", 30))
        limit_value = int(data.get("limit_value", 0))

        # Get subscription plan
        plan = SubscriptionPlan.objects.filter(name=plan_name).first()
        if not plan:
            return Response({"message": "Invalid plan"}, status=status.HTTP_400_BAD_REQUEST)

        subscription_price = plan.price

        # Get or create wallet
        wallet, _ = Wallet.objects.get_or_create(user=user)

        # Check balance
        if wallet.reel_bux_balance < subscription_price:
            return Response({"message": "Insufficient ReelBux balance"}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct balance
        wallet.reel_bux_balance -= subscription_price
        wallet.save()

        # Generate unique subscription ID
        subs_id = f"reelbux_{uuid.uuid4().hex[:16]}"

        # Create subscription
        subscription = UserSubscription.objects.create(
            user=user,
            plan_name=plan_name,
            payment_method="reelbux",
            subscription_id=subs_id,
            price=subscription_price,
            limit_value=limit_value,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=duration_days),
            cancel_at_period_end=False,
            payment_status="completed",
            status="active",
        )

        # Mark user as subscribed
        user.is_subscribe = True  # or is_subscribed if that's your field
        user.save()

        # Log transaction
        Transaction.objects.create(
            user=user,
            source="reelbux",
            tx_type="subscription",
            amount=subscription_price,
            txn_id=subs_id,
            balance_type="reelbux",
            status="completed",
            description=f"Debit {subscription_price} ReelBux for subscription",
        )

        return Response({
            "message": "Subscription activated using ReelBux balance.",
            "subscription_id": subscription.subscription_id,
            "new_balance": wallet.reel_bux_balance
        }, status=status.HTTP_201_CREATED)
