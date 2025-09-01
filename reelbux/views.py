from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from subscription.models import Wallet, Transaction

class MyReelBuxView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get or create wallet for this user
        wallet, created = Wallet.objects.get_or_create(user=user)

        # Retrieve transactions of specific types
        allowed_tx_types = ['fund', 'purchase', 'rent', 'subscription']
        txn_history = Transaction.objects.filter(
            user=user,
            tx_type__in=allowed_tx_types
        ).order_by('-created_at')[:10]

        txn_data = [
            {
                "source": t.get_source_display(),
                "tx_type": t.get_tx_type_display(),
                "amount": t.amount,
                "date": t.created_at.strftime("%d %B %Y"),
                "status": t.get_status_display(),
            }
            for t in txn_history
        ]

        return Response({
            "status": "success",
            "message": "Wallet fetched successfully",
            "reel_bux_balance": wallet.reel_bux_balance,
            "txn_data": txn_data,
        })
