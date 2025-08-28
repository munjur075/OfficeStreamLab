import uuid
from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

import paypalrestsdk
from .models import Wallet, Transaction

# -------------------- PAYPAL CONFIG --------------------
paypalrestsdk.configure({
    "mode": "sandbox",  # change to "live" in production
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET,
})


# -------------------- CREATE ADD FUNDS --------------------
class CreatePaypalAddFundsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        amount = float(request.data.get("amount", 0))
        currency = "USD"
        payment_method = "paypal"

        if amount <= 0:
            return Response({"error": "Invalid amount"}, status=400)

        # Create PayPal Payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": request.build_absolute_uri(
                    reverse("subscription:paypal_addfunds_execute")
                ),
                "cancel_url": request.build_absolute_uri(
                    reverse("subscription:paypal_addfunds_cancel")
                ),
            },
            "transactions": [{
                "item_list": {"items": [{
                    "name": "Wallet Top-up",
                    "sku": str(uuid.uuid4()),
                    "price": f"{amount:.2f}",
                    "currency": currency,
                    "quantity": 1,
                }]},
                "amount": {"total": f"{amount:.2f}", "currency": currency},
                "description": f"Add {amount} {currency} to wallet",
            }],
        })

        if payment.create():
            approval_url = next(link.href for link in payment.links if link.rel == "approval_url")
            token = approval_url.split("token=")[1]

            # Save pending transaction
            Transaction.objects.create(
                user=user,
                source="paypal",
                tx_type="fund",
                amount=Decimal(amount),
                balance_type="reelbux",
                status="pending",   # always start as pending
                reference_id=payment.id,  # PayPal payment ID
                paypal_token=token,
                description=f"Wallet top-up via {payment_method}"
            )

            return Response({"approvalUrl": approval_url})

        return Response({"error": payment.error}, status=500)


# -------------------- EXECUTE ADD FUNDS --------------------
class ExecutePaypalAddFundsView(APIView):
    authentication_classes = []  # PayPal redirects (no JWT)
    permission_classes = []

    def get(self, request, *args, **kwargs):
        payment_id = request.query_params.get("paymentId")
        payer_id = request.query_params.get("PayerID")

        if not payment_id:
            return Response({"error": "Missing paymentId"}, status=400)

        try:
            payment = paypalrestsdk.Payment.find(payment_id)
        except Exception as e:
            return Response({"error": f"Payment not found: {str(e)}"}, status=400)

        # Cancel case (missing payer_id)
        if not payer_id:
            Transaction.objects.filter(
                reference_id=payment_id, status="pending"
            ).update(status="failed")
            return Response(
                {"status": "cancelled", "message": "User cancelled at PayPal."},
                status=200
            )

        # Execute PayPal payment
        if payment.execute({"payer_id": payer_id}):
            try:
                transaction = Transaction.objects.select_related("user").get(reference_id=payment_id)
                transaction.status = "success"
                transaction.save()

                # Update wallet balance
                wallet, _ = Wallet.objects.get_or_create(user=transaction.user)
                wallet.reel_bux_balance += transaction.amount
                wallet.save(update_fields=["reel_bux_balance", "updated_at"])

                return Response({
                    "status": "success",
                    "message": f"Added {transaction.amount} {transaction.balance_type} wallet."
                })

            except Transaction.DoesNotExist:
                return Response({"error": "Transaction record not found."}, status=404)

        # Failed execution
        Transaction.objects.filter(reference_id=payment_id).update(status="failed")
        return Response({"error": payment.error}, status=400)


# -------------------- CANCEL ADD FUNDS --------------------
def paypal_addfunds_cancel_view(request):
    token = request.GET.get("token")
    if token:
        # PayPal sends token in cancel redirect
        Transaction.objects.filter(paypal_token=token, status="pending").update(status="failed")
    return JsonResponse({"status": "cancelled", "message": "Add Funds was cancelled by user."})
