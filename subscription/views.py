# subscriptions/views.py
import json
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from .models import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import *
stripe.api_key = settings.STRIPE_SECRET_KEY


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        plan = data.get("plan")
        price_map = {
            "Basic": settings.STRIPE_PRICE_BASIC,
            "Pro": settings.STRIPE_PRICE_PRO,
            "Enterprise": settings.STRIPE_PRICE_ELITE,
        }
        price_id = price_map.get(plan)
        # print(price_id)
        if not price_id:
            return Response({"error": "invalid plan"}, status=400)

        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                customer_email=request.user.email,
                subscription_data={"metadata": {"django_user_id": str(request.user.id), "plan": plan}},
                success_url=request.build_absolute_uri(reverse("subscription:checkout_success")) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=request.build_absolute_uri(reverse("subscription:checkout_cancel")),
            )
            print(session)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

        return Response({
        "sessionId": session.id,
        "checkoutUrl": session.url
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




def checkout_success(request):
    return JsonResponse({
        "status": "success",
        "message": "Subscription successful! You can now access premium features."
    })

def checkout_cancel(request):
    return JsonResponse({
        "status": "cancelled",
        "message": "Subscription process was cancelled. You can try again anytime."
    })
