# from paypal.standard.models import ST_PP_COMPLETED
# from paypal.standard.ipn.signals import valid_ipn_received
# from django.dispatch import receiver
# from django.utils import timezone
# from datetime import timedelta
# from accounts.models import User
# from .models import UserSubscription, SubscriptionPlan

# @receiver(valid_ipn_received)
# def paypal_ipn_receiver(sender, **kwargs):
#     ipn = sender
#     if ipn.payment_status != ST_PP_COMPLETED:
#         return

#     try:
#         user = User.objects.get(id=ipn.custom)
#         user_email = user.email
#         plan = SubscriptionPlan.objects.filter(name=ipn.item_name).first()
#         if not plan:
#             return

#         if UserSubscription.objects.filter(subscription_id=ipn.invoice).exists():
#             return

#         now = timezone.now()
#         UserSubscription.objects.create(
#             user=user_email,
#             plan_name=plan.name,
#             price=plan.price,
#             payment_method='paypal',
#             subscription_id=ipn.invoice,
#             current_period_start=now,
#             current_period_end=now + timedelta(days=30),
#             payment_status='completed',
#             status='active',
#         )

#         user.is_subscribe = True
#         user.save()
#         print(f"Subscription saved for {user.email}")

#     except Exception as e:
#         print("PayPal IPN error:", e)




# from paypal.standard.models import ST_PP_COMPLETED
# from paypal.standard.ipn.signals import valid_ipn_received
# from django.dispatch import receiver
# from accounts.models import User

# @receiver(valid_ipn_received)
# def paypal_payment_notification(sender, **kwargs):
#     print('MMMMMMMMMMMMMM----')
#     ipn = sender
#     if ipn.payment_status == ST_PP_COMPLETED:
#         user_id = ipn.custom
#         try:
#             user = User.objects.get(id=user_id)
#             user.is_subscribe = True
#             user.save()
#         except User.DoesNotExist:
#             pass

