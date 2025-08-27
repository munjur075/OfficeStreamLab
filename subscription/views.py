
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from .models import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import SubscriptionPlan
from accounts.models import User
from .serializers import *
stripe.api_key = settings.STRIPE_SECRET_KEY


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        subscribe_user = User.objects.get(email=user)

        if subscribe_user.is_subscribe:
            return Response({"message": "You are already subscribed! Please cancel your existing subscription If you wish to update it."}, status=status.HTTP_200_OK)
        
        data = request.data
        plan = data.get("plan")
        duration_days = data.get("duration_days")
        limit_value = data.get("limit_value", 0)
        plan_name = SubscriptionPlan.objects.filter(name=plan).first()
        if not plan_name:
            return Response({"error": "invalid plan"}, status=400)

        price_map = {
            "Basic": settings.STRIPE_PRICE_BASIC,
            "Pro": settings.STRIPE_PRICE_PRO,
            "Elite": settings.STRIPE_PRICE_ELITE,
        }
        price_id = price_map.get(plan)
        # print(price_id)
        if not price_id:
            return Response({"error": "invalid plan"}, status=400)

        try:
            checkout_session = stripe.checkout.Session.create(
                mode="subscription",
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                customer_email=request.user.email,
                metadata= {"user_id": str(request.user.id), "plan": plan, "duration_days": int(duration_days), "limit_value": int(limit_value)},
                success_url=request.build_absolute_uri(reverse("subscription:stripe_checkout_success")) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=request.build_absolute_uri(reverse("subscription:stripe_checkout_cancel")),
            )
            # print(session)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

        return Response({
        "sessionId": checkout_session.id,
        "checkoutUrl": checkout_session.url
    })

    def get(self, request, *args, **kwargs):
        user = request.user
        subscription_details = UserSubscription.objects.filter(user=user).first()

        if not subscription_details:
            return Response(
                {"status": "error", "message": "No subscription found for this user."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SubscriptionSerializer(subscription_details)
        return Response(
            {"status": "success", "data": serializer.data},
            status=status.HTTP_200_OK
        )


def stripe_checkout_success_view(request):
    return JsonResponse({
        "status": "success",
        "message": "Subscription successful! You can now access premium features."
    })

def stripe_checkout_cancel_view(request):
    return JsonResponse({
        "status": "cancelled",
        "message": "Subscription process was cancelled. You can try again anytime."
    })


