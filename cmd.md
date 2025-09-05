#
stripe login
<!-- stripe listen --forward-to localhost:8000/api/payment/webhook/ -->
<!--for Ai subscription -->
stripe listen --forward-to localhost:8000/api/payment/stripe/webhook/subscription/

<!--for Add Funds -->
stripe listen --forward-to localhost:8000/api/payment/stripe/webhook/add-funds/

<!--for Film Purchase -->
stripe listen --forward-to localhost:8000/api/flims/stripe/webhook/purchase

# Deploy Static
ngrok http --url=equal-evidently-terrier.ngrok-free.app 8000

# Changeable
ngrok http http://localhost:8080

# request body
    film_id = request.data.get("film_id")
# request Params
    search_param = request.GET.get("search", "").strip()

# How to do AND / OR logic in Django ORM queries.
🔹AND Logic
    from myapp.models import Transaction
    # Example: user=1 AND tx_type='fund'
    Transaction.objects.filter(user=1, tx_type='fund')

🔹OR Logic
    from django.db.models import Q
    # Example: tx_type='fund' OR tx_type='rent'
    Transaction.objects.filter(Q(tx_type='fund') | Q(tx_type='rent'))

🔹Combining AND + OR
    # Example: user=1 AND (tx_type='fund' OR tx_type='rent')
    Transaction.objects.filter(
        user=1
    ).filter(
        Q(tx_type='fund') | Q(tx_type='rent')
    )

    Or equivalently:
        Transaction.objects.filter(
            Q(user=1) & (Q(tx_type='fund') | Q(tx_type='rent'))
        )

card:
4242 4242 4242 4242
