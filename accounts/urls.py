from django.urls import path
from accounts import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:user_id>/edit/', views.staff_edit, name='staff_edit'),
]
