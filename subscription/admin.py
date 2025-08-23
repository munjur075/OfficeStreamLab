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
    list_display = ('user', 'tx_type', 'amount', 'balance_type', 'status', 'source', 'created_at')
    list_filter = ('tx_type', 'status', 'balance_type', 'source')
    search_fields = ('user__email', 'reference_id')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


# -------------------- WITHDRAWALS --------------------
@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'transaction', 'requested_at', 'processed_at')
    list_filter = ('status',)
    search_fields = ('user__email', 'transaction__reference_id')
    readonly_fields = ('requested_at', 'processed_at')
    ordering = ('-requested_at',)


# -------------------- PLAN FEATURE --------------------
@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


# -------------------- PLAN FEATURE ASSIGNMENT INLINE --------------------
class PlanFeatureAssignmentInline(admin.TabularInline):
    model = PlanFeatureAssignment
    extra = 1


# -------------------- SUBSCRIPTION PLAN --------------------
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_highlighted', 'limit_value', 'duration_days', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_highlighted',)
    inlines = [PlanFeatureAssignmentInline]
    readonly_fields = ('created_at',)


# -------------------- USER SUBSCRIPTIONS --------------------
@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'payment_method', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'payment_method')
    search_fields = ('user__email', 'plan__name')
    readonly_fields = ('start_date', 'end_date')
    ordering = ('-start_date',)

