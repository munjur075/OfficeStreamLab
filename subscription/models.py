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
        return f"Wallet of {self.user.email}"


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
        return f"{self.user.email} - {self.tx_type} {self.amount} ({self.get_status_display()})"


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
        return f"Withdrawal {self.amount} by {self.user.email} ({self.status})"


# -------------------- PLAN FEATURE --------------------
class PlanFeature(models.Model):
    """
    Represents a type of feature (e.g., AI generations, Video generations, Image generations etc.)
    """
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name


# -------------------- SUBSCRIPTION PLAN --------------------
class SubscriptionPlan(models.Model):
    """
    Subscription plan like Basic, Pro, Enterprise.
    Each plan has different limits (plan-wise, not per feature).
    """
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional: store an icon name (FontAwesome/Bootstrap) or emoji."
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_highlighted = models.BooleanField(default=False)

    features = models.ManyToManyField(
        "PlanFeature",
        through="PlanFeatureAssignment",
        related_name="plans"
    )

    # PLAN-WISE LIMIT
    limit_value = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Set a numeric limit for the whole plan. Leave empty/0 for unlimited."
    )

    duration_days = models.PositiveIntegerField(default=30, help_text="Plan duration in days")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        limit_text = "Unlimited" if not self.limit_value else self.limit_value
        return f"{self.name} (${self.price}) - Limit: {limit_text} ({self.duration_days} days)"


# -------------------- PLAN FEATURE ASSIGNMENT --------------------
class PlanFeatureAssignment(models.Model):
    """
    Links a SubscriptionPlan with a PlanFeature.
    No per-feature limit; just inclusion/exclusion.
    """
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    feature = models.ForeignKey(PlanFeature, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("plan", "feature")

    def __str__(self):
        return f"{self.plan.name} → {self.feature.name}"


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
            duration = self.plan.duration_days if self.plan else 30
            self.end_date = self.start_date + timedelta(days=duration)
        super().save(*args, **kwargs)

    def __str__(self):
        status = "Active" if self.active else "Expired"
        return f"{self.user.email} - {self.plan.name} ({status})"


# -------------------- SUBSCRIPTION USAGE --------------------
class SubscriptionUsage(models.Model):
    """
    Track how much of a subscription plan the user has consumed (plan-wise usage).
    Example:
        User A - Basic Plan: used 120 out of 200 credits
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscription_usage")
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name="usage")

    used_value = models.PositiveIntegerField(default=0)         # actual usage count
    free_used_value = models.PositiveIntegerField(default=0)    # free quota usage (if any)

    class Meta:
        verbose_name = "Subscription Usage"
        verbose_name_plural = "Subscription Usages"
        unique_together = ("user", "subscription")  # one usage record per user-subscription

    def __str__(self):
        return f"{self.user.email} - {self.subscription.plan.name}: {self.used_value}"

