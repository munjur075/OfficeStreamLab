from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

User = settings.AUTH_USER_MODEL


# -------------------- WALLET --------------------
class Wallet(models.Model):
    """
    Each user has one wallet with two balances:
    - reel_bux_balance: can be funded via Stripe/PayPal or transferred from Distro.
    - distro_balance: affiliate earnings; can be transferred to ReelBux or withdrawn.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    reel_bux_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    distro_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"

    def __str__(self):
        return f"Wallet of {self.user}"


# -------------------- TRANSACTIONS --------------------
class Transaction(models.Model):
    """Record all wallet movements (credits and debits)."""

    SOURCE_CHOICES = [
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
        ("reelbux", "ReelBux"),
        ("distro", "Distro"),
        ("system", "System"),
    ]

    TYPE_CHOICES = [
        ("fund", "Fund Wallet"),
        ("transfer", "Transfer Distro → ReelBux"),
        ("withdraw", "Withdraw from Distro"),
        ("purchase", "Buy Film"),
        ("rent", "Rent Film"),
        ("commission", "Affiliate Commission"),
    ]

    BALANCE_CHOICES = [
        ("reelbux", "ReelBux"),
        ("distro", "Distro"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    tx_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_type = models.CharField(
        max_length=20,
        choices=BALANCE_CHOICES,
        null=True,
        blank=True,
        help_text="Which balance was affected?"
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["tx_type"]),
            models.Index(fields=["balance_type"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.tx_type} {self.amount} ({self.source})"


# -------------------- SUBSCRIPTIONS --------------------
class SubscriptionPlan(models.Model):
    """Available subscription plans (e.g., Basic, Pro, Enterprise)."""

    DURATION_CHOICES = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    name = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=20, choices=DURATION_CHOICES, default="monthly")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"

    def __str__(self):
        return f"{self.name} ({self.price} / {self.duration})"


class Subscription(models.Model):
    """User subscriptions (linked to plans and payment methods)."""

    PAYMENT_METHODS = [
        ("reelbux", "ReelBux"),
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name="subscriptions")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
        ordering = ["-start_date"]

    def save(self, *args, **kwargs):
        # auto-calc end_date if missing
        if not self.end_date:
            if self.plan.duration == "monthly":
                self.end_date = self.start_date + timedelta(days=30)
            elif self.plan.duration == "yearly":
                self.end_date = self.start_date + timedelta(days=365)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.plan.name} ({'Active' if self.active else 'Expired'})"

