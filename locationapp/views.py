from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Employee, Attendance, SalaryAdjustment, calculate_distance, OFFICE_LAT, OFFICE_LON
from datetime import date, datetime, timedelta
from calendar import monthrange
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum

try:
    from django.utils.http import url_has_allowed_host_and_scheme
except ImportError:
    from django.utils.http import is_safe_url
    url_has_allowed_host_and_scheme = is_safe_url


# ========================= AUTO CHECK-OUT FUNCTION =========================

def auto_checkout_if_far(employee, lat, lon):
    """
    Automatically check out employee if they move >100m from office
    Returns: (checked_out: bool, distance: float)
    """
    distance = round(calculate_distance(lat, lon, OFFICE_LAT, OFFICE_LON), 2)
    
    # Check if employee is currently checked in
    if employee.is_checked_in and distance > 100:
        # Find today's active attendance (checked in but not checked out)
        today_attendance = Attendance.objects.filter(
            employee=employee,
            date=date.today(),
            check_in_time__isnull=False,
            check_out_time__isnull=True
        ).order_by('-id').first()
        
        if today_attendance:
            # Auto check-out
            today_attendance.check_out_time = timezone.now()
            today_attendance.auto_checkout = True
            today_attendance.checkout_reason = f"Auto checkout - moved {distance}m from office"
            today_attendance.save()
            
            # Update employee status
            employee.is_checked_in = False
            employee.save()
            
            return True, distance
    
    return False, distance


# ========================= ATTENDENCE SECTION =========================
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import Employee, Attendance

def attendance_dashboard(request):
    emp = get_object_or_404(Employee, E_id=request.GET.get('E_id'))
    today = timezone.localdate()
    today_record = Attendance.objects.filter(employee=emp, date=today).order_by('-check_in_time').first()
    context = {
        'emp': emp,
        'today_record': today_record,
    }
    return render(request, 'attendance_dashboard.html', context)

def check_in(request):
    emp = get_object_or_404(Employee, E_id=request.GET.get('E_id'))
    now = timezone.now()
    Attendance.objects.create(employee=emp, date=now.date(), check_in_time=now, status='Present')
    return redirect('attendance_dashboard')

def check_out(request):
    emp = get_object_or_404(Employee, E_id=request.GET.get('E_id'))
    today = timezone.localdate()
    att = Attendance.objects.filter(employee=emp, date=today, check_out_time__isnull=True).first()
    if att:
        att.check_out_time = timezone.now()
        att.save()
    return redirect('attendance_dashboard')


# ========================= ENHANCED SALARY CALCULATION =========================

from django.shortcuts import render
from .models import Employee, Attendance
from datetime import date
def employee_salary_summary(request):
    E_id = request.GET.get("E_id")
    if not E_id:
        return render(request, "employee_salary_dashboard.html", {"error": "No Employee ID provided."})
    try:
        emp = Employee.objects.get(E_id=E_id)
    except Employee.DoesNotExist:
        return render(request, "employee_salary_dashboard.html", {"error": "Invalid Employee ID."})
    
    today = date.today()
    month = today.month
    year = today.year

    attendances = Attendance.objects.filter(
        employee=emp, date__year=year, date__month=month, status="Present"
    )

    standard_hours = emp.standard_hours_per_day
    monthly_salary = float(emp.monthly_salary)
    hourly_rate = float(emp.hourly_rate)

    total_hours = sum(a.hours_worked() for a in attendances)
    full_days = sum(1 for a in attendances if a.hours_worked() >= standard_hours)
    partial_days = attendances.count() - full_days

    if emp.salary_type == 'monthly':
        daily_rate = monthly_salary / 26
        base_hours = sum(min(a.hours_worked(), standard_hours) for a in attendances)
        salary_for_days = (base_hours / (standard_hours * 26)) * monthly_salary
        overtime_hours = sum(max(a.hours_worked() - standard_hours, 0) for a in attendances)
        overtime_money = overtime_hours * hourly_rate * 1.5  # 1.5x multiplier
        salary_formula = (
            f"({base_hours:.2f}h ÷ {standard_hours*26}h) × ₹{monthly_salary:.2f}"
            f" + {overtime_hours:.2f}h × ₹{hourly_rate*1.5:.2f} (overtime)"
        )
        this_month_income = salary_for_days + overtime_money
    else:
        salary_for_days = total_hours * hourly_rate
        overtime_hours = 0
        overtime_money = 0
        salary_formula = f"{total_hours:.2f}h × ₹{hourly_rate:.2f}/hour"
        this_month_income = salary_for_days

    context = {
        "emp": emp,
        "month": month,
        "year": year,
        "salary_type": emp.salary_type,
        "full_days": full_days,
        "partial_days": partial_days,
        "total_days_present": attendances.count(),
        "total_hours": round(total_hours, 2),
        "salary_for_days": round(salary_for_days, 2),
        "overtime_hours": round(overtime_hours, 2),
        "overtime_money": round(overtime_money, 2),
        "hourly_rate": hourly_rate,
        "monthly_salary": monthly_salary,
        "salary_formula": salary_formula,
        "this_month_income": round(this_month_income, 2),
    }
    return render(request, "employee_salary_dashboard.html", context)



# ========================= UPDATE HOME VIEW (Check-in with Sunday detection) =========================


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
            emp.last_location_update = timezone.now()
            emp.save()

            # Check for auto-checkout
            auto_checked_out, distance = auto_checkout_if_far(emp, lat, lon)
            if auto_checked_out:
                return render(request, "home.html", {
                    "warning": f"⚠️ You were automatically checked out because you moved {distance}m from office.",
                    "auto_checkout": True
                })

            if distance > 100:
                return render(request, "home.html", {
                    "error": f"You are not within 100 meters! (Distance: {distance} m)"
                })

            # Check if today is Sunday
            today = date.today()
            is_sunday = (today.weekday() == 6)

            # Create attendance record
            Attendance.objects.create(
                employee=emp, 
                status="Present", 
                latitude=lat, 
                longitude=lon,
                check_in_time=timezone.now(),
                checkout_reason="Manual check-in",
                is_sunday=is_sunday
            )
            emp.is_checked_in = True
            emp.save()

            # ---- RENDER dashboard directly here ----
            records = Attendance.objects.filter(employee=emp).order_by("-date")
            today_record = records.filter(date=date.today()).first()
            year = date.today().year
            month = date.today().month
            total_days = 26  # Your standard working days

            attendance_map = {}
            for day in range(1, total_days + 1):
                day_date = date(year, month, day)
                latest_attendance = Attendance.objects.filter(employee=emp, date=day_date).order_by('-id').first()
                attendance_map[day] = latest_attendance.status if latest_attendance else "Absent"

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



# Keep all other views from previous code...
# (auto_checkout_if_far, checkout, update_location, etc.)



# ========================= LOCATION UPDATE (for auto-checkout monitoring) =========================

@login_required
def update_location(request):
    """
    API endpoint for continuous location monitoring
    Called by frontend every minute to check if employee has moved away
    """
    if request.method == "POST":
        lat = request.POST.get("latitude")
        lon = request.POST.get("longitude")
        
        if not lat or not lon:
            return JsonResponse({"error": "Location not provided"}, status=400)
        
        lat = float(lat)
        lon = float(lon)
        
        emp = Employee.objects.filter(user=request.user).first()
        if not emp:
            return JsonResponse({"error": "Employee not found"}, status=404)
        
        # Update location
        emp.latitude = lat
        emp.longitude = lon
        emp.last_location_update = timezone.now()
        emp.save()
        
        # Check if auto-checkout needed
        auto_checked_out, distance = auto_checkout_if_far(emp, lat, lon)
        
        return JsonResponse({
            "success": True,
            "distance": distance,
            "auto_checked_out": auto_checked_out,
            "is_checked_in": emp.is_checked_in,
            "message": f"Auto checked out - {distance}m from office" if auto_checked_out else "Location updated"
        })
    
    return JsonResponse({"error": "Invalid request"}, status=400)


# ========================= EMPLOYEE DETAILS API =========================

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
            "monthly_salary": float(emp.monthly_salary),
            "hourly_rate": float(emp.hourly_rate),
            "salary_type": emp.salary_type,
            "is_manager": emp.is_manager,
            "latitude": emp.latitude,
            "longitude": emp.longitude,
        }
        return JsonResponse(data)
    except Employee.DoesNotExist:
        return JsonResponse({"error": "Employee not found"}, status=404)


# ========================= LOGIN =========================

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


# ========================= LOGOUT =========================

def user_logout(request):
    logout(request)
    return redirect("home")


def custom_admin_logout(request):
    """Logout and redirect to home page"""
    logout(request)
    return redirect('home')


# ========================= MANUAL CHECKOUT ========================

def checkout(request):
    """Handle manual checkout"""
    # Get employee by session or POST data
    E_id = request.GET.get("E_id") or request.POST.get("E_id")
    
    if not E_id:
        return redirect('home')
    
    try:
        emp = Employee.objects.get(E_id=E_id)
    except Employee.DoesNotExist:
        return redirect('home')
    
    # Get today's attendance record
    today = date.today()
    today_record = Attendance.objects.filter(
        employee=emp, 
        date=today,
        status='Present'
    ).first()
    
    if today_record and today_record.check_in_time and not today_record.check_out_time:
        # Record check-out time
        today_record.check_out_time = timezone.now()
        today_record.checkout_reason = "Manual checkout"
        today_record.auto_checkout = False
        today_record.save()
        
        # Update employee status
        emp.is_checked_in = False
        emp.save()
        
        # Calculate hours worked (this triggers the hours_worked() method)
        hours = today_record.hours_worked()
        
        # Success message (optional)
        print(f"✅ {emp.E_name} checked out. Worked {hours} hours today.")
    
    # Redirect to home page
    return redirect('home')



# ========================= EMPLOYEE SALARY VIEW =========================

@login_required
def employee_salary_report(request):
    """Employee view to see their own salary"""
    emp = Employee.objects.filter(user=request.user).first()
    
    if not emp:
        return redirect("login")
    
    # Get year and month from request or use current
    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', date.today().month))
    
    salary_data = calculate_monthly_salary(emp.id, year, month)
    salary_data['is_employee_view'] = True
    
    return render(request, 'employee_salary.html', salary_data)



from datetime import datetime
from django.utils import timezone

def calculate_monthly_salary(employee, month=None, year=None):
    """
    Calculate monthly salary for an employee based on attendance
    """
    if month is None:
        month = timezone.now().month
    if year is None:
        year = timezone.now().year
    
    # Get all attendance records for the month
    attendance_records = Attendance.objects.filter(
        employee=employee,
        date__month=month,
        date__year=year,
        status='Present'
    )
    
    # Calculate totals
    total_hours = sum(record.hours_worked() for record in attendance_records)
    overtime_hours = sum(record.overtime_hours() for record in attendance_records)
    
    # Hourly rate, safe for field or method
    if hasattr(employee, 'hourly_rate'):
        hr = getattr(employee, 'hourly_rate')
        hourly_rate = hr() if callable(hr) else hr
    else:
        hourly_rate = employee.salary / (employee.standard_hours_per_day * 22)
    
    # Calculate salary
    if employee.salary_type == 'hourly':
        base_salary = total_hours * float(hourly_rate)
    else:
        base_salary = float(employee.salary)
    
    # Add overtime
    overtime_pay = overtime_hours * float(hourly_rate) * 1.5
    
    total_salary = base_salary + overtime_pay
    
    return {
        'base_salary': round(base_salary, 2),
        'overtime_pay': round(overtime_pay, 2),
        'total_salary': round(total_salary, 2),
        'total_hours': round(total_hours, 2),
        'overtime_hours': round(overtime_hours, 2),
        'hourly_rate': round(float(hourly_rate), 2),
        'total_days_present': attendance_records.count()
    }

# ========================= MANAGER SALARY VIEWS =========================

@login_required
def manager_salary_overview(request):
    """Manager view to see all employee salaries"""
    # Get current month/year or from request
    month = int(request.GET.get('month', timezone.now().month))
    year = int(request.GET.get('year', timezone.now().year))
    
    # Get all employees
    employees = Employee.objects.all()
    
    salary_data = []
    for emp in employees:
        # Calculate salary for this employee
        salary_info = calculate_monthly_salary(emp, month, year)
        
        salary_data.append({
            'employee': emp,
            'E_id': emp.E_id,
            'E_name': emp.E_name,
            'base_salary': salary_info['base_salary'],
            'overtime_pay': salary_info['overtime_pay'],
            'total_salary': salary_info['total_salary'],
            'total_hours': salary_info['total_hours'],
            'overtime_hours': salary_info['overtime_hours'],
            'total_days_present': salary_info['total_days_present']
        })
    
    context = {
        'salary_data': salary_data,
        'month': month,
        'year': year
    }
    
    return render(request, 'manager_salary_overview.html', context)



@login_required
def adjust_salary(request, employee_id):
    """HR can manually adjust calculated salary"""
    emp = Employee.objects.filter(user=request.user).first()
    
    if not emp or not emp.is_manager:
        return redirect("employee_dashboard")
    
    if not request.user.has_perm('locationapp.can_manipulate_salary'):
        return redirect("manager_salary_overview")
    
    employee = get_object_or_404(Employee, id=employee_id)
    
    # Get year and month
    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', date.today().month))
    
    salary_data = calculate_monthly_salary(employee_id, year, month)
    
    if request.method == "POST":
        adjusted_salary = request.POST.get("adjusted_salary")
        reason = request.POST.get("reason")
        
        if adjusted_salary and reason:
            # Create or update adjustment
            adjustment, created = SalaryAdjustment.objects.update_or_create(
                employee=employee,
                month=month,
                year=year,
                defaults={
                    'calculated_salary': salary_data['calculated_salary'],
                    'adjusted_salary': float(adjusted_salary),
                    'adjustment_reason': reason,
                    'adjusted_by': request.user,
                }
            )
            return redirect(f"/manager/salary/{employee_id}/view/?year={year}&month={month}")
    
    context = salary_data
    context.update({
        'year': year,
        'month': month,
        'emp': emp,
    })
    
    return render(request, 'adjust_salary.html', context)


@login_required
def view_employee_salary_detail(request, employee_id):
    """Detailed salary view for HR"""
    emp = Employee.objects.filter(user=request.user).first()
    
    if not emp or not emp.is_manager:
        return redirect("employee_dashboard")
    
    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', date.today().month))
    
    salary_data = calculate_monthly_salary(employee_id, year, month)
    salary_data.update({
        'year': year,
        'month': month,
        'emp': emp,
        'can_manipulate': request.user.has_perm('locationapp.can_manipulate_salary'),
    })
    
    return render(request, 'salary_detail.html', salary_data)


# ========================= GREETING HELPER =========================

def get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"


# ========================= ADD USER/EMPLOYEE VIEWS (Keep your existing ones) =========================

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
        salary_type = request.POST.get("salary_type")
        monthly_salary = request.POST.get("monthly_salary") or 0
        hourly_rate = request.POST.get("hourly_rate") or 0
        role = request.POST.get("role")

        if not all([username, password, E_id, E_name]):
            return render(request, "add_user.html", {
                "error": "All required fields must be filled."
            })

        if User.objects.filter(username=username).exists():
            return render(request, "add_user.html", {
                "error": "Username already exists."
            })

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
                salary_type=salary_type,
                monthly_salary=monthly_salary,
                hourly_rate=hourly_rate,
                is_manager=(role == "Manager")
            )

            return redirect("manager_dashboard")
        except Exception as e:
            return render(request, "add_user.html", {
                "error": f"Error creating user: {str(e)}"
            })

    return render(request, "add_user.html")


@login_required
def add_employee(request):
    emp = Employee.objects.filter(user=request.user).first()

    if not emp or not emp.is_manager:
        return redirect("employee_dashboard")

    if request.method == "POST":
        E_id = request.POST.get("E_id")
        E_name = request.POST.get("E_name")
        salary_type = request.POST.get("salary_type")
        monthly_salary = request.POST.get("monthly_salary") or 0
        hourly_rate = request.POST.get("hourly_rate") or 0
        is_manager = request.POST.get("is_manager") == "on"

        if not all([E_id, E_name]):
            return render(request, "add_employee.html", {
                "error": "All required fields must be filled."
            })

        if Employee.objects.filter(E_id=E_id).exists():
            return render(request, "add_employee.html", {
                "error": "Employee ID already exists."
            })

        try:
            Employee.objects.create(
                E_id=E_id,
                E_name=E_name,
                salary_type=salary_type,
                monthly_salary=monthly_salary,
                hourly_rate=hourly_rate,
                is_manager=is_manager
            )

            return redirect("manager_dashboard")
        except Exception as e:
            return render(request, "add_employee.html", {
                "error": f"Error creating employee: {str(e)}"
            })

    return render(request, "add_employee.html")


# ========================= MANAGER DASHBOARD =========================

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

    employees = []
    for e in employees_raw:
        present_count = attendance.filter(employee=e, status='Present').count()
        absent_count = attendance.filter(employee=e, status='Absent').count()
        employees.append({
            'E_name': e.E_name,
            'E_id': e.E_id,
            'salary': e.salary,
            'salary_type': e.get_salary_type_display(),
            'id': e.id,
            'present_count': present_count,
            'absent_count': absent_count,
        })

    total_present = attendance.filter(status='Present').count()
    total_absent = attendance.filter(status='Absent').count()
    
    error = None
    success = None
    
    if request.method == "POST" and permissions['can_add_employee']:
        E_id = request.POST.get("E_id")
        E_name = request.POST.get("E_name")
        salary_type = request.POST.get("salary_type")
        monthly_salary = request.POST.get("monthly_salary") or 0
        hourly_rate = request.POST.get("hourly_rate") or 0
        is_manager = request.POST.get("is_manager") == "on"
        
        if not all([E_id, E_name]):
            error = "All fields are required."
        elif Employee.objects.filter(E_id=E_id).exists():
            error = "Employee ID already exists."
        else:
            try:
                Employee.objects.create(
                    E_id=E_id,
                    E_name=E_name,
                    salary_type=salary_type,
                    monthly_salary=monthly_salary,
                    hourly_rate=hourly_rate,
                    is_manager=is_manager
                )
                success = f"Employee {E_name} added successfully!"
                # Refresh list
                employees_raw = Employee.objects.all()
                employees = []
                for e in employees_raw:
                    present_count = attendance.filter(employee=e, status='Present').count()
                    absent_count = attendance.filter(employee=e, status='Absent').count()
                    employees.append({
                        'E_name': e.E_name,
                        'E_id': e.E_id,
                        'salary': e.salary,
                        'salary_type': e.get_salary_type_display(),
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


@login_required
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
    
    return render(request, 'edit_salary.html', {'employee': employee})


@login_required
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


# ========================= EMPLOYEE DASHBOARD =========================

@login_required
def employee_dashboard(request):
    emp = Employee.objects.filter(user=request.user).first()
    
    if not emp:
        return redirect("login")

    records = Attendance.objects.filter(employee=emp).order_by("-date")
    today_record = records.filter(date=date.today()).first()

    year = date.today().year
    month = date.today().month
    total_days = monthrange(year, month)[1]

    attendance_map = {}
    
    for day in range(1, total_days + 1):
        day_date = date(year, month, day)
        latest_attendance = Attendance.objects.filter(
            employee=emp, 
            date=day_date
        ).order_by('-id').first()
        
        if latest_attendance:
            attendance_map[day] = latest_attendance.status
        else:
            attendance_map[day] = "Absent"

    return render(request, "employee_dashboard.html", {
        "emp": emp,
        "records": records,
        "today_record": today_record,
        "attendance_map": attendance_map,
        "year": year,
        "month": month,
        "total_days": total_days,
    })
