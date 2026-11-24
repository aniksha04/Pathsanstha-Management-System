from django.urls import path
from loans import views

urlpatterns = [
    path('', views.loan_list, name='loan_list'),
    path('apply/', views.loan_apply, name='loan_apply'),
    path('<int:pk>/', views.loan_detail, name='loan_detail'),
    path('<int:pk>/approve/', views.loan_approve, name='loan_approve'),
    path('<int:pk>/reject/', views.loan_reject, name='loan_reject'),
    path('<int:pk>/disburse/', views.loan_disburse, name='loan_disburse'),
    path('<int:pk>/repay/<int:repayment_id>/', views.loan_collect_payment, name='loan_collect_payment'),
    path('receipt/<int:payment_id>/', views.loan_receipt, name='loan_receipt'),
]
