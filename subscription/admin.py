from django.contrib import admin
from .models import Wallet, Transaction, SubscriptionPlan, Subscription

# Wallet(ReelBux & Distro)
admin.site.register(Wallet)
admin.site.register(Transaction)

# Subscription
admin.site.register(SubscriptionPlan)
admin.site.register(Subscription)