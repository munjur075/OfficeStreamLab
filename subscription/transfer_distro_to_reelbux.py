
from decimal import Decimal
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Wallet, Transaction


class TransferDistroToReelBuxAPIView(APIView):
    """Transfer user’s affiliate (distro) balance → ReelBux balance."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        amount = request.data.get("amount")

        # Validate amount
        if not amount:
            return Response({"error": "Amount is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(amount)
        except:
            return Response({"error": "Invalid amount format."}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"error": "Amount must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)

        wallet = Wallet.objects.select_for_update().get(user=user)

        if wallet.distro_balance < amount:
            return Response({"error": "Insufficient distro balance."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Deduct from distro
            wallet.distro_balance -= amount

            # Credit to reelbux
            wallet.reel_bux_balance += amount
            wallet.save()

            # Log transaction - debit from distro
            Transaction.objects.create(
                user=user,
                source="distro",
                tx_type="transfer",
                amount=amount,
                balance_type="distro",
                status="success",
                description=f"Transferred {amount} from Distro to ReelBux",
            )

            # Log transaction - credit to reelbux
            Transaction.objects.create(
                user=user,
                source="reelbux",
                tx_type="transfer",
                amount=amount,
                balance_type="reelbux",
                status="success",
                description=f"Received {amount} from Distro",
            )

        return Response(
            {
                "message": "Transfer successful",
                "amount": str(amount),
                "new_balances": {
                    "distro_balance": str(wallet.distro_balance),
                    "reel_bux_balance": str(wallet.reel_bux_balance),
                },
            },
            status=status.HTTP_200_OK,
        )
