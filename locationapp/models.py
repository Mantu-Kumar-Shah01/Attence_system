from django.db import models
from django.contrib.auth.models import User
from math import radians, sin, cos, sqrt, atan2

# Fixed office coordinates
OFFICE_LAT = 30.866745
OFFICE_LON = 75.924881


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    E_id = models.CharField(max_length=10, unique=True)
    E_name = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_manager = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.E_name} ({self.E_id})"


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10)  # Present/Absent
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee.E_name} - {self.date} - {self.status}"


# Haversine formula — returns distance in meters
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c
