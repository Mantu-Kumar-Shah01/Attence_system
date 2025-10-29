from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("add_user/", views.add_user, name="add_user"),
    path("manager_dashboard/", views.manager_dashboard, name="manager_dashboard"),
    path("employee_dashboard/", views.employee_dashboard, name="employee_dashboard"),
    path("employee_details/", views.employee_details, name="employee_details"),
]
