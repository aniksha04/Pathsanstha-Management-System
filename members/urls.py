from django.urls import path
from members import views

urlpatterns = [
    path('', views.member_list, name='member_list'),
    path('register/', views.member_register, name='member_register'),
    path('<int:pk>/', views.member_detail, name='member_detail'),
    path('<int:pk>/edit/', views.member_edit, name='member_edit'),
    path('<int:pk>/toggle-status/', views.member_toggle_status, name='member_toggle_status'),
]
