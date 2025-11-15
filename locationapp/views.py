from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Employee, Attendance, calculate_distance, OFFICE_LAT, OFFICE_LON
from datetime import date
from calendar import monthrange
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Employee, Attendance
from datetime import datetime

try:
    from django.utils.http import url_has_allowed_host_and_scheme
except ImportError:
    from django.utils.http import is_safe_url
    url_has_allowed_host_and_scheme = is_safe_url


# ------------------------- HOME (Attendance Marking) -------------------------
def home(request):
    if request.method == "POST":
        E_id = request.POST.get("E_id")
        lat = request.POST.get("latitude")
        lon = request.POST.get("longitude")

        if not lat or not lon:
            return render(request, "home.html", {"error": "Location not detected!"})

        lat = float(lat)
        lon = float(lon)

        try:
            emp = Employee.objects.get(E_id=E_id)
            emp.latitude = lat
            emp.longitude = lon
            emp.save()

            distance = round(calculate_distance(lat, lon, OFFICE_LAT, OFFICE_LON), 2)

            if distance > 100:
                return render(request, "home.html", {
                    "error": f"You are not within 100 meters! (Distance: {distance} m)"
                })

            # Mark attendance
            Attendance.objects.create(
                employee=emp, status="Present", latitude=lat, longitude=lon
            )

            # Get updated records
            records = Attendance.objects.filter(employee=emp).order_by("-date")
            today_record = records.filter(date=date.today()).first()

            # Build attendance_map with latest status per day
            year = date.today().year
            month = date.today().month
            total_days = monthrange(year, month)[1]

            attendance_map = {}
            for day in range(1, total_days + 1):
                day_date = date(year, month, day)
                latest = Attendance.objects.filter(employee=emp, date=day_date).order_by('-id').first()
                attendance_map[day] = latest.status if latest else "Absent"

            return render(request, "employee_dashboard.html", {
                "emp": emp,
                "records": records,
                "today_record": today_record,
                "attendance_map": attendance_map,
                "year": year,
                "month": month,
                "total_days": total_days,
            })

        except Employee.DoesNotExist:
            return render(request, "home.html", {"error": "Invalid Employee ID"})

    return render(request, "home.html")


# ------------------------- EMPLOYEE DETAILS API -------------------------
def employee_details(request):
    E_id = request.GET.get("E_id")
    if not E_id:
        return JsonResponse({"error": "E_id is required"}, status=400)

    try:
        emp = Employee.objects.get(E_id=E_id)
        data = {
            "E_id": emp.E_id,
            "E_name": emp.E_name,
            "salary": float(emp.salary),
            "is_manager": emp.is_manager,
            "latitude": emp.latitude,
            "longitude": emp.longitude,
        }
        return JsonResponse(data)
    except Employee.DoesNotExist:
        return JsonResponse({"error": "Employee not found"}, status=404)


# ------------------------- LOGIN -------------------------
@csrf_protect
def user_login(request):
    next_url = request.GET.get("next") or request.POST.get("next") or "/"

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if not user or not user.is_active:
            return render(request, "login.html", {
                "error": "Invalid username, password, or inactive user.",
                "next": next_url
            })

        login(request, user)

        allowed_hosts = {request.get_host()}
        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts=allowed_hosts):
            next_url = "/"

        if user.is_superuser:
            return redirect("/admin/")

        emp = Employee.objects.filter(user=user).first()

        if not emp:
            logout(request)
            return render(request, "login.html", {
                "error": "No employee profile linked to this user.",
                "next": next_url
            })

        if emp.is_manager:
            return redirect("manager_dashboard")

        return redirect("employee_dashboard")

    return render(request, "login.html", {"next": next_url})

# ------------------------- LOGOUT -------------------------
def user_logout(request):
    logout(request)
    return redirect("home")  # ✅ Redirect to home instead of login

from django.contrib.auth import logout
from django.shortcuts import redirect

def custom_admin_logout(request):
    """Logout and redirect to home page"""
    logout(request)
    return redirect('home')


# ------------------------- ADD USER -------------------------
@login_required
def add_user(request):
    emp = Employee.objects.filter(user=request.user).first()

    if not emp or not emp.is_manager:
        return redirect("employee_dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        E_id = request.POST.get("E_id")
        E_name = request.POST.get("E_name")
        salary = request.POST.get("salary")
        role = request.POST.get("role")

        # Validate required fields
        if not all([username, password, E_id, E_name, salary]):
            return render(request, "add_user.html", {
                "error": "All fields are required."
            })

        # Check for duplicate username
        if User.objects.filter(username=username).exists():
            return render(request, "add_user.html", {
                "error": "Username already exists."
            })

        # Check for duplicate Employee ID
        if Employee.objects.filter(E_id=E_id).exists():
            return render(request, "add_user.html", {
                "error": "Employee ID already exists."
            })

        try:
            user = User.objects.create_user(username=username, password=password)

            Employee.objects.create(
                user=user,
                E_id=E_id,
                E_name=E_name,
                salary=salary,
                is_manager=(role == "Manager")
            )

            return redirect("manager_dashboard")
        except Exception as e:
            return render(request, "add_user.html", {
                "error": f"Error creating user: {str(e)}"
            })

    return render(request, "add_user.html")

# ------------------------- ADD USER -------------------------

def add_employee(request):
    emp = Employee.objects.filter(user=request.user).first()

    if not emp or not emp.is_manager:
        return redirect("employee_dashboard")

    if request.method == "POST":
        E_id = request.POST.get("E_id")
        E_name = request.POST.get("E_name")
        salary = request.POST.get("salary")
        is_manager = request.POST.get("is_manager") == "on"  # checkbox value

        # Validate required fields
        if not all([E_id, E_name, salary]):
            return render(request, "add_employee.html", {
                "error": "All fields are required."
            })

        # Check for duplicate Employee ID
        if Employee.objects.filter(E_id=E_id).exists():
            return render(request, "add_employee.html", {
                "error": "Employee ID already exists."
            })

        try:
            Employee.objects.create(
                E_id=E_id,
                E_name=E_name,
                salary=salary,
                is_manager=is_manager
            )

            return redirect("manager_dashboard")
        except Exception as e:
            return render(request, "add_employee.html", {
                "error": f"Error creating employee: {str(e)}"
            })

    return render(request, "add_employee.html")

# ------------------------- GREETING MANAGER -------------------------


def get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"

# ------------------------- MANAGER DASHBOARD -------------------------
@login_required
def manager_dashboard(request):
    emp = Employee.objects.filter(user=request.user).first()
    greeting = get_greeting() 
    
    if not emp or not emp.is_manager:
        return redirect("employee_dashboard")
    
    user_permissions = request.user.get_all_permissions()
    
    permissions = {
        'can_view_attendance': 'locationapp.can_view_attendance' in user_permissions,
        'can_edit_salary': 'locationapp.can_edit_salary' in user_permissions,
        'can_add_employee': 'locationapp.can_add_employee' in user_permissions,
        'can_delete_employee': 'locationapp.can_delete_employee' in user_permissions,
        'can_view_reports': 'locationapp.can_view_reports' in user_permissions,
    }
    
    employees_raw = Employee.objects.all()
    attendance = Attendance.objects.all()

    # Add present and absent count for each employee
    employees = []
    for e in employees_raw:
        present_count = attendance.filter(employee=e, status='Present').count()
        absent_count = attendance.filter(employee=e, status='Absent').count()
        employees.append({
            'E_name': e.E_name,
            'E_id': e.E_id,
            'salary': e.salary,
            'id': e.id,
            'present_count': present_count,
            'absent_count': absent_count,
        })

    total_present = attendance.filter(status='Present').count()
    total_absent = attendance.filter(status='Absent').count()
    
    error = None
    success = None
    
    # Handle Add Employee form submission
    if request.method == "POST" and permissions['can_add_employee']:
        E_id = request.POST.get("E_id")
        E_name = request.POST.get("E_name")
        salary = request.POST.get("salary")
        is_manager = request.POST.get("is_manager") == "on"
        
        if not all([E_id, E_name, salary]):
            error = "All fields are required."
        elif Employee.objects.filter(E_id=E_id).exists():
            error = "Employee ID already exists."
        else:
            try:
                Employee.objects.create(
                    E_id=E_id,
                    E_name=E_name,
                    salary=salary,
                    is_manager=is_manager
                )
                success = f"Employee {E_name} added successfully!"
                # Refresh list after adding
                employees_raw = Employee.objects.all()
                employees = []
                for e in employees_raw:
                    present_count = attendance.filter(employee=e, status='Present').count()
                    absent_count = attendance.filter(employee=e, status='Absent').count()
                    employees.append({
                        'E_name': e.E_name,
                        'E_id': e.E_id,
                        'salary': e.salary,
                        'id': e.id,
                        'present_count': present_count,
                        'absent_count': absent_count,
                    })
            except Exception as e:
                error = f"Error creating employee: {str(e)}"
    
    context = {
        'emp': emp,
        'employees': employees,
        'attendance': attendance,
        'permissions': permissions,
        'total_present': total_present,
        'total_absent': total_absent,
        'error': error,
        'success': success,
        'greeting': greeting,
    }
    
    return render(request, 'manager_dashboard.html', context)
def edit_salary(request, employee_id):
    emp = Employee.objects.filter(user=request.user).first()
    
    if not emp or not emp.is_manager:
        return redirect("employee_dashboard")
    
    if not request.user.has_perm('locationapp.can_edit_salary'):
        return redirect("manager_dashboard")
    
    employee = get_object_or_404(Employee, id=employee_id)
    
    if request.method == "POST":
        new_salary = request.POST.get("salary")
        
        if new_salary and float(new_salary) >= 0:
            employee.salary = float(new_salary)
            employee.save()
            return redirect("manager_dashboard")
        else:
            return render(request, 'edit_salary.html', {
                'employee': employee,
                'error': 'Invalid salary amount.'
            })
    attendance = Attendance.objects.all()

    total_present = attendance.filter(status='Present').count()
    total_absent = attendance.filter(status='Absent').count()

   
    return render(request, 'edit_salary.html', {'employee': employee})


# ✅ DELETE EMPLOYEE VIEW
def delete_employee(request, employee_id):
    emp = Employee.objects.filter(user=request.user).first()
    
    if not emp or not emp.is_manager:
        return redirect("employee_dashboard")
    
    if not request.user.has_perm('locationapp.can_delete_employee'):
        return redirect("manager_dashboard")
    
    employee = get_object_or_404(Employee, id=employee_id)
    
    if request.method == "POST":
        employee.delete()
        return redirect("manager_dashboard")
    
    return render(request, 'delete_employee.html', {'employee': employee})


# ------------------------- EMPLOYEE DASHBOARD -------------------------
@login_required
def employee_dashboard(request):
    emp = Employee.objects.filter(user=request.user).first()
    
    if not emp:
        return redirect("login")

    # Get all attendance records
    records = Attendance.objects.filter(employee=emp).order_by("-date")
    today_record = records.filter(date=date.today()).first()

    # Build calendar with LATEST status for each day
    year = date.today().year
    month = date.today().month
    total_days = monthrange(year, month)[1]

    attendance_map = {}
    
    # ✅ For each day, get the LATEST attendance record
    for day in range(1, total_days + 1):
        day_date = date(year, month, day)
        
        # Get the latest attendance for that day
        latest_attendance = Attendance.objects.filter(
            employee=emp, 
            date=day_date
        ).order_by('-id').first()  # ✅ Get most recent record
        
        if latest_attendance:
            attendance_map[day] = latest_attendance.status
        else:
            attendance_map[day] = "Absent"  # ✅ If no record, mark as Absent

    return render(request, "employee_dashboard.html", {
        "emp": emp,
        "records": records,
        "today_record": today_record,
        "attendance_map": attendance_map,
        "year": year,
        "month": month,
        "total_days": total_days,
    })