#
stripe login
stripe listen --forward-to localhost:8000/api/payment/webhook/

# Deploy Static
ngrok http --url=equal-evidently-terrier.ngrok-free.app 8000