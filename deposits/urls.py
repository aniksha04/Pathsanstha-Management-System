from django.urls import path
from deposits import views

urlpatterns = [
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/<int:pk>/', views.account_detail, name='account_detail'),
    path('accounts/<int:pk>/toggle-status/', views.account_toggle_status, name='account_toggle_status'),
    path('deposit/', views.deposit_create, name='deposit_create'),
    path('withdrawal/', views.withdrawal_create, name='withdrawal_create'),
]
