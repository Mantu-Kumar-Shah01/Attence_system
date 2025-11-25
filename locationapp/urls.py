from django.urls import path
from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path('admin-logout/', views.custom_admin_logout, name='custom_admin_logout'),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("employee_details/", views.employee_details, name="employee_details"),
    
    # Employee Dashboard
    path("employee_dashboard/", views.employee_dashboard, name="employee_dashboard"),
    
    # Manager Dashboard
    path("manager_dashboard/", views.manager_dashboard, name="manager_dashboard"),
    
    # Employee Management
    path("add_user/", views.add_user, name="add_user"),
    path('add_employee/', views.add_employee, name='add_employee'),
    path('edit_salary/<int:employee_id>/', views.edit_salary, name='edit_salary'),
    path('delete_employee/<int:employee_id>/', views.delete_employee, name='delete_employee'),
    
    # ✅ NEW: Check-in/Check-out
    path('checkout/', views.checkout, name='checkout'),
    path('update_location/', views.update_location, name='update_location'),  # For auto-checkout
    
    # ✅ NEW: Employee Salary Views
      path("my-salary/", views.employee_salary_summary, name="employee_salary_summary"),
    
    # ✅ NEW: Manager Salary Views
    path('manager/salary-overview/', views.manager_salary_overview, name='manager_salary_overview'),
    path('manager/salary/<int:employee_id>/view/', views.view_employee_salary_detail, name='view_salary_detail'),
    path('manager/salary/<int:employee_id>/adjust/', views.adjust_salary, name='adjust_salary'),
]
