from django.db import models
from django.utils import timezone
from datetime import timedelta
from accounts.models import User

# -------------------- WALLET --------------------
class Wallet(models.Model):
    """
    Each user has one wallet with two balances:
    - reel_bux_balance: funded via Stripe/PayPal or transferred from Distro.
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
    """Records all wallet movements (credits and debits)."""

    SOURCE_CHOICES = [
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
        ("reelbux", "ReelBux"),
        ("distro", "Distro"),
        ("system", "System"),
    ]

    TYPE_CHOICES = [
        ("fund", "Add Fund"),
        ("transfer", "Transfer Distro → ReelBux"),
        ("withdraw", "Withdraw from Distro"),
        ("purchase", "Buy Film"),
        ("rent", "Rent Film"),
        ("commission", "Distro Commission"),
        ("subscription", "AI Subscription"),
    ]

    BALANCE_CHOICES = [
        ("reelbux", "ReelBux"),
        ("distro", "Distro"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    tx_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_type = models.CharField(max_length=20, choices=BALANCE_CHOICES, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reference_id = models.CharField(max_length=100, blank=True, help_text="Stripe/PayPal TXN ID")
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


# -------------------- WITHDRAWALS --------------------
class Withdrawal(models.Model):
    """Distro balance withdrawal requests."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("paid", "Paid"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Withdrawal"
        verbose_name_plural = "Withdrawals"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Withdrawal {self.amount} by {self.user} ({self.status})"



#
# -------------------- PLAN FEATURE --------------------
class PlanFeature(models.Model):
    """
    Represents a type of feature (e.g., AI generations, Video length, Image resolution).
    """
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


# -------------------- SUBSCRIPTION PLAN --------------------
class SubscriptionPlan(models.Model):
    """
    Subscription plan like Basic, Pro, Enterprise.
    Each plan has different limits for features.
    """
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True)  # e.g., "StarIcon"
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_highlighted = models.BooleanField(default=False)
    features = models.ManyToManyField(
        PlanFeature,
        through='PlanFeatureAssignment',
        related_name='plans'
    )

    limit_value = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Set a numeric limit. Leave empty or 0 for unlimited."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        if self.limit_value and self.limit_value > 0:
            return f"{self.plan.name} - {self.feature.name}: {self.limit_value}"
        return f"{self.plan.name} - {self.feature.name}: Unlimited"

    def __str__(self):
        return f"{self.name} (${self.price})"


# -------------------- PLAN FEATURE ASSIGNMENT --------------------
class PlanFeatureAssignment(models.Model):
    """
    Through table:
    Links SubscriptionPlan <-> PlanFeature with per-plan limit.
    Example:
        Basic - AI Generations - 200
        Pro - AI Generations - 500
        Enterprise - AI Generations - Unlimited (limit_value = 0 or NULL)
    """
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    feature = models.ForeignKey(PlanFeature, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('plan', 'feature')



# -------------------- USER SUBSCRIPTIONS --------------------
class UserSubscription(models.Model):
    """
    Tracks user subscriptions to plans.
    Automatically calculates end_date based on plan duration.
    """
    PAYMENT_METHODS = [
        ("reelbux", "ReelBux"),
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name="user_subscriptions")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "User Subscription"
        verbose_name_plural = "User Subscriptions"
        ordering = ["-start_date"]

    def save(self, *args, **kwargs):
        # auto-calculate end_date if missing
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=30)  # default 1 month
        super().save(*args, **kwargs)

    def __str__(self):
        status = "Active" if self.active else "Expired"
        return f"{self.user} - {self.plan.name} ({status})"


# -------------------- SUBSCRIPTION USAGE TRACKING --------------------
class SubscriptionUsage(models.Model):
    """
    Track how much of each feature a user has consumed
    under a specific subscription plan.
    Example:
        User A - Basic Plan - AI Generations: used 120/200
        User A - Basic Plan - Video Minutes: used 30/120
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscription_usage")
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name="usage")
    # feature = models.ForeignKey(PlanFeature, on_delete=models.CASCADE, related_name="usage")

    ai_used_value = models.PositiveIntegerField(default=0)        # actual usage count
    free_ai_used_value = models.PositiveIntegerField(default=0)   # free quota usage

    class Meta:
        verbose_name = "Subscription Usage"
        verbose_name_plural = "Subscription Usages"
        unique_together = ("user", "subscription")  # avoid duplicates

    def __str__(self):
        return f"{self.user} - {self.subscription.plan.name}: {self.ai_used_value}"
