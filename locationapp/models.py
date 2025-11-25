from django.db import models
from django.contrib.auth.models import User
from math import radians, sin, cos, sqrt, atan2
from datetime import timedelta, datetime

# Fixed office coordinates
OFFICE_LAT = 30.8665825
OFFICE_LON = 75.9249735

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    E_id = models.CharField(max_length=10, unique=True)
    E_name = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Salary Configuration
    SALARY_TYPE_CHOICES = [
        ('monthly', 'Monthly Fixed (Days-based)'),
        ('hourly', 'Hourly Rate (Hours-based)'),
    ]
    salary_type = models.CharField(
        max_length=10, 
        choices=SALARY_TYPE_CHOICES, 
        default='monthly',
        help_text="Select salary calculation method"
    )
    
    monthly_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.0,
        help_text="Fixed monthly salary (for 26 working days)"
    )
    
    hourly_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.0,
        help_text="Hourly rate in ₹"
    )
    
    # Working hours configuration
    standard_hours_per_day = models.IntegerField(
        default=8, 
        help_text="Standard working hours per day (8 hours = 1 full day)"
    )
    
    overtime_rate_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.5,
        help_text="Overtime rate multiplier (1.5 = 150% of hourly rate)"
    )
    
    # Legacy field
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    
    is_manager = models.BooleanField(default=False)
    is_checked_in = models.BooleanField(default=False)
    last_location_update = models.DateTimeField(null=True, blank=True)

    class Meta:
        permissions = [
            ('can_view_attendance', 'Can view attendance records'),
            ('can_edit_salary', 'Can edit employee salary'),
            ('can_add_employee', 'Can add new employees'),
            ('can_delete_employee', 'Can delete employees'),
            ('can_view_reports', 'Can view reports'),
            ('can_manipulate_salary', 'Can manipulate calculated salary'),
        ]

    def __str__(self):
        return f"{self.E_name} ({self.E_id})"


class Attendance(models.Model):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10)  # Present/Absent
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    auto_checkout = models.BooleanField(default=False)
    checkout_reason = models.CharField(max_length=100, null=True, blank=True)
    is_sunday = models.BooleanField(default=False)
    is_holiday = models.BooleanField(default=False)
    manual_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    adjustment_reason = models.TextField(null=True, blank=True)

    @property
    def hours_worked(self):
        if self.manual_hours is not None:
            return float(self.manual_hours)
        if self.check_in_time and self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            hours = delta.total_seconds() / 3600
            return round(hours, 2)
        return 0.0

    def hours_worked(self):
        """Calculate total hours worked"""
        if self.manual_hours is not None:
            return float(self.manual_hours)
        
        if self.check_in_time and self.check_out_time:
            duration = self.check_out_time - self.check_in_time
            hours = duration.total_seconds() / 3600
            return round(hours, 2)
        
        if self.check_in_time and not self.check_out_time:
            return float(self.employee.standard_hours_per_day)
        
        return 0
    
    def regular_hours(self):
        """Calculate regular hours (up to 8 hours)"""
        total = self.hours_worked()
        standard = self.employee.standard_hours_per_day
        return min(total, standard)
    
    def overtime_hours(self):
        """Calculate overtime hours (beyond 8 hours or Sunday work)"""
        total = self.hours_worked()
        standard = self.employee.standard_hours_per_day
        
        if self.is_sunday or self.is_holiday:
            # All hours on Sunday/holiday are overtime
            return total
        else:
            # Only hours beyond standard are overtime
            return max(0, total - standard)
    
    def full_days_equivalent(self):
        """Calculate how many full days this represents (8 hours = 1 day)"""
        return round(self.regular_hours() / self.employee.standard_hours_per_day, 2)

    def __str__(self):
        return f"{self.employee.E_name} - {self.date} - {self.status}"


class SalaryAdjustment(models.Model):
    """Model to track HR manual salary adjustments"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    month = models.IntegerField()
    year = models.IntegerField()
    calculated_salary = models.DecimalField(max_digits=10, decimal_places=2)
    adjusted_salary = models.DecimalField(max_digits=10, decimal_places=2)
    adjustment_reason = models.TextField()
    adjusted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    adjusted_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['employee', 'month', 'year']
    
    def __str__(self):
        return f"{self.employee.E_name} - {self.month}/{self.year} - ₹{self.adjusted_salary}"


# Haversine formula
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c
