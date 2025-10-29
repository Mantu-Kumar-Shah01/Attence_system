from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Employee, Attendance, calculate_distance, OFFICE_LAT, OFFICE_LON
from datetime import date


# ------------------------- HOME (Attendance Marking) -------------------------
def home(request):
    if request.method == "POST":
        E_id = request.POST.get("E_id")
        lat = float(request.POST.get("latitude"))
        lon = float(request.POST.get("longitude"))

        try:
            emp = Employee.objects.get(E_id=E_id)
            emp.latitude, emp.longitude = lat, lon
            emp.save()

            distance = calculate_distance(lat, lon, OFFICE_LAT, OFFICE_LON)
            status = "Present" if distance <= 100 else "Absent"

            Attendance.objects.create(
                employee=emp, status=status, latitude=lat, longitude=lon
            )

            # After marking attendance, render an employee details page
            records = Attendance.objects.filter(employee=emp).order_by("-date")
            today_record = records.filter(date=date.today()).first()
            return render(
                request,
                "employee_dashboard.html",
                {"emp": emp, "records": records, "today_record": today_record},
            )
        except Employee.DoesNotExist:
            return render(request, "home.html", {"error": "Invalid Employee ID"})
    return render(request, "home.html")


# ------------------------- EMPLOYEE DETAILS (by E_id) -------------------------
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


# ------------------------- LOGIN / LOGOUT -------------------------
def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            emp = Employee.objects.filter(user=user).first()
            if emp is None:
                return render(request, "login.html", {"error": "No employee profile linked to this user."})
            if emp.is_manager:
                return redirect("manager_dashboard")
            return redirect("employee_dashboard")
        return render(request, "login.html", {"error": "Invalid Credentials"})
    return render(request, "login.html")


def user_logout(request):
    logout(request)
    return redirect("login")


# ------------------------- ADD USER -------------------------
@login_required
def add_user(request):
    emp = Employee.objects.get(user=request.user)
    if not emp.is_manager:
        return redirect("employee_dashboard")

    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        E_id = request.POST["E_id"]
        E_name = request.POST["E_name"]
        salary = request.POST["salary"]
        role = request.POST["role"]  # Manager or Employee

        user = User.objects.create_user(username=username, password=password)
        Employee.objects.create(
            user=user,
            E_id=E_id,
            E_name=E_name,
            salary=salary,
            is_manager=True if role == "Manager" else False,
        )
        return redirect("manager_dashboard")

    return render(request, "add_user.html")


# ------------------------- DASHBOARDS -------------------------
@login_required
def manager_dashboard(request):
    emp = Employee.objects.get(user=request.user)
    if not emp.is_manager:
        return redirect("employee_dashboard")

    employees = Employee.objects.all()
    attendance = Attendance.objects.all().order_by("-date")
    return render(
        request,
        "manager_dashboard.html",
        {"employees": employees, "attendance": attendance, "emp": emp},
    )


@login_required
def employee_dashboard(request):
    emp = Employee.objects.get(user=request.user)
    records = Attendance.objects.filter(employee=emp).order_by("-date")
    today_record = records.filter(date=date.today()).first()
    return render(
        request,
        "employee_dashboard.html",
        {"emp": emp, "records": records, "today_record": today_record},
    )
