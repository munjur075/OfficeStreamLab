from django.urls import path
from .views import UserManagementView, AdminFilmsView, SubscriptionManagementView
from .film_delete import *
from .film_approve_reject import *
from .distro_reports import *

urlpatterns = [
    #1 Admin Dashboard
    # path('dashboard', AdminDashboardView.as_view(), name='dashboard'),

    #2 User Management
    path('manage-users', UserManagementView.as_view(), name='manage_users'),

    #3 Films
    path('films', AdminFilmsView.as_view(), name='films'),
    path('films-delete', FilmDeleteView.as_view(), name='films_delete'),
    path('films-approve-reject', FilmApproveRejectView.as_view(), name='films_approve_reject'),

    #5 Distro
    path('distro-report', FilmDistroReportView.as_view(), name='distro_report'),

    #6 Subscriber Management SubscriptionManagementView
    path('subscribers', SubscriptionManagementView.as_view(), name='subscribers'),
]
