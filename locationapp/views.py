from django.shortcuts import render
from django.http import JsonResponse
from math import radians, sin, cos, sqrt, atan2
from .models import Employee

# Fixed office location (change as per your location)
OFFICE_LAT = 30.866755
OFFICE_LON = 75.924881

def home(request):
    """Show the attendance page"""
    return render(request, 'home.html')

def save_location(request):
    """Receive location and mark attendance if within 100m"""
    if request.method == 'POST':
        e_id = request.POST.get('E_id')
        lat = float(request.POST.get('latitude'))
        lon = float(request.POST.get('longitude'))

        try:
            emp = Employee.objects.get(E_id=e_id)
        except Employee.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Employee ID not found'})

        # Calculate distance (Haversine formula)
        R = 6371000  # Earth radius in meters
        dlat = radians(lat - OFFICE_LAT)
        dlon = radians(lon - OFFICE_LON)
        a = sin(dlat/2)**2 + cos(radians(OFFICE_LAT)) * cos(radians(lat)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c

        if distance <= 100:
            emp.attendance_status = "Present"
            emp.save()
            return JsonResponse({'status': 'success', 'message': f'Attendance marked! Distance: {int(distance)} m'})
        else:
            return JsonResponse({'status': 'error', 'message': f'Too far from office ({int(distance)} m away)'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
