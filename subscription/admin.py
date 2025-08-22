from django.contrib import admin
from .models import (
    Wallet, Transaction, Withdrawal,
    PlanFeature, SubscriptionPlan, PlanFeatureAssignment,
    UserSubscription, SubscriptionUsage
)

# -------------------- WALLET --------------------
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "reel_bux_balance", "distro_balance", "updated_at")
    search_fields = ("user__email",)


# -------------------- TRANSACTIONS --------------------
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "tx_type", "amount", "balance_type", "source", "status", "created_at")
    list_filter = ("tx_type", "balance_type", "source", "status")
    search_fields = ("user__email", "reference_id")
    ordering = ("-created_at",)


# -------------------- WITHDRAWALS --------------------
@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "status", "requested_at", "processed_at")
    list_filter = ("status",)
    search_fields = ("user__email",)


# -------------------- PLAN FEATURE --------------------
@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


# -------------------- PLAN FEATURE INLINE --------------------
class PlanFeatureAssignmentInline(admin.TabularInline):
    model = PlanFeatureAssignment
    extra = 1
    autocomplete_fields = ("feature",)


# -------------------- SUBSCRIPTION PLAN --------------------
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "price", "is_highlighted", "created_at")
    list_filter = ("is_highlighted",)
    search_fields = ("name",)
    inlines = [PlanFeatureAssignmentInline]


# -------------------- USER SUBSCRIPTION --------------------
@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "payment_method", "start_date", "end_date", "active")
    list_filter = ("active", "payment_method", "plan")
    search_fields = ("user__email", "plan__name")


# -------------------- SUBSCRIPTION USAGE --------------------
@admin.register(SubscriptionUsage)
class SubscriptionUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "subscription", "ai_used_value", "free_ai_used_value")
    list_filter = ("subscription__plan",)
    search_fields = ("user__email",)
