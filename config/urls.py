"""
URL configuration for Pathsanstha Management System project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('branches/', include('branches.urls')),
    path('members/', include('members.urls')),
    path('deposits/', include('deposits.urls')),
    path('loans/', include('loans.urls')),
    path('transactions/', include('transactions.urls')),
    path('reports/', include('reports.urls')),
    path('', RedirectView.as_view(url='/reports/', permanent=False)),
]
