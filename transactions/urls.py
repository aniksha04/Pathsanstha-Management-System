from django.urls import path
from transactions import views

urlpatterns = [
    path('', views.transaction_list, name='transaction_list'),
    path('<int:pk>/', views.transaction_detail, name='transaction_detail'),
]
