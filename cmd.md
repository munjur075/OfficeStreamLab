#
stripe login
<!-- stripe listen --forward-to localhost:8000/api/payment/webhook/ -->
<!--for Ai subscription -->
stripe listen --forward-to localhost:8000/api/payment/stripe/webhook/subscription/

<!--for Add Funds -->
stripe listen --forward-to localhost:8000/api/payment/stripe/webhook/add-funds/

# Deploy Static
ngrok http --url=equal-evidently-terrier.ngrok-free.app 8000

# Changeable
ngrok http http://localhost:8080