from django.db import models

class Employee(models.Model):
    E_id = models.CharField(max_length=10, unique=True)
    E_name = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.E_name} ({self.E_id})"
from django.db import models

class Employee(models.Model):
    E_id = models.CharField(max_length=20, unique=True)
    E_name = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    attendance_status = models.CharField(max_length=20, default='Absent')

    def __str__(self):
        return f"{self.E_name} ({self.E_id})"
