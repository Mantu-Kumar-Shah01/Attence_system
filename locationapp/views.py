from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Employee, Attendance, calculate_distance, OFFICE_LAT, OFFICE_LON
from datetime import date
from calendar import monthrange


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
    next_url = request.GET.get("next") or request.POST.get("next", "/")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if not user:
            return render(request, "login.html", {
                "error": "Invalid username or password.",
                "next": next_url
            })

        login(request, user)

        # SUPERUSER → Admin Panel
        if user.is_superuser:
            return redirect("/admin/")

        # NORMAL USER (must have Employee profile)
        emp = Employee.objects.filter(user=user).first()

        if not emp:
            logout(request)
            return render(request, "login.html", {
                "error": "No employee profile linked.",
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


# ------------------------- MANAGER DASHBOARD -------------------------
@login_required
def manager_dashboard(request):
    emp = Employee.objects.filter(user=request.user).first()

    if not emp:
        return redirect("login")

    if not emp.is_manager:
        return redirect("employee_dashboard")

    employees = Employee.objects.all()
    attendance = Attendance.objects.all().order_by("-date")

    return render(request, "manager_dashboard.html", {
        "employees": employees,
        "attendance": attendance,
        "emp": emp,
    })


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