from django.contrib import admin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import path, include
from django.views.decorators.csrf import csrf_protect

@csrf_protect
def admin_logout_custom(request):
    """Custom admin logout that redirects to home page"""
    logout(request)
    return redirect('home')

urlpatterns = [
    path("admin/logout/", admin_logout_custom, name="admin_logout_custom"),
    path("admin/", admin.site.urls),
    path("", include("locationapp.urls")),
]
