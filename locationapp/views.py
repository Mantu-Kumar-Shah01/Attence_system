from django.shortcuts import render
from django.http import JsonResponse
from .models import Employee

def home(request):
    return render(request, 'home.html')

def save_location(request):
    if request.method == "POST":
        e_id = request.POST.get("E_id")
        lat = request.POST.get("latitude")
        lon = request.POST.get("longitude")

        try:
            emp = Employee.objects.get(E_id=e_id)
            emp.latitude = lat
            emp.longitude = lon
            emp.save()
            return JsonResponse({"status": "success"})
        except Employee.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Employee not found"})
