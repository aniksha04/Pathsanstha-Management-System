from django.urls import path
from branches import views

urlpatterns = [
    path('', views.branch_list, name='branch_list'),
    path('create/', views.branch_create, name='branch_create'),
    path('<int:pk>/', views.branch_detail, name='branch_detail'),
    path('<int:pk>/edit/', views.branch_edit, name='branch_edit'),
]
