from django.contrib import admin
from .models import (
    Wallet, Transaction, Withdrawal,
    PlanFeature, SubscriptionPlan, PlanFeatureAssignment,
    UserSubscription
)


# -------------------- WALLET --------------------
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'reel_bux_balance', 'distro_balance', 'updated_at')
    search_fields = ('user__email',)
    readonly_fields = ('updated_at',)


# -------------------- TRANSACTIONS --------------------
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'tx_type', 'amount', 'txn_id', 'balance_type', 'status', 'source', 'created_at')
    list_filter = ('tx_type', 'status', 'balance_type', 'source')
    search_fields = ('user__email', 'txn_id')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


# -------------------- WITHDRAWALS --------------------
@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'transaction', 'requested_at', 'processed_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'transaction__txn_id')
    readonly_fields = ('requested_at', 'processed_at')
    ordering = ('-requested_at',)


# -------------------- PLAN FEATURE --------------------
@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


# -------------------- PLAN FEATURE ASSIGNMENT --------------------
class PlanFeatureAssignmentInline(admin.TabularInline):
    model = PlanFeatureAssignment
    extra = 1
    verbose_name = "Feature Assignment"
    verbose_name_plural = "Feature Assignments"


# -------------------- SUBSCRIPTION PLAN --------------------
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'limit_value', 'is_highlighted', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_highlighted', 'duration_days')
    inlines = [PlanFeatureAssignmentInline]


# -------------------- USER SUBSCRIPTION --------------------
# admin.site.register(UserSubscription)

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_name', 'payment_method', 'subscription_id', 'price', 'used_value', 'free_used_value', 'limit_value', 'current_period_start', 'current_period_end', 'payment_status', 'status',)