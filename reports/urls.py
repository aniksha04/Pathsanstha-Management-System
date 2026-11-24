from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('loans/', views.loan_summary, name='loan_summary'),
]