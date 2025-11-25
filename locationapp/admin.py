from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Attendance, SalaryAdjustment


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'name_display', 'role_display', 'salary_type_display', 'rate_display']
    list_filter = ['is_manager', 'salary_type', 'user__date_joined']
    search_fields = ['E_id', 'E_name']
    ordering = ['-id']
    readonly_fields = ['latitude', 'longitude', 'location_display', 'is_checked_in', 'last_location_update']
    
    fieldsets = (
        ('👤 Basic Information', {
            'fields': ('user', 'E_id', 'E_name'),
            'classes': ('wide',)
        }),
        ('💼 Employment Details', {
            'fields': ('is_manager', 'salary_type', 'monthly_salary', 'hourly_rate', 'standard_hours_per_day', 'salary'),
        }),
        ('📍 Location & Status', {
            'fields': ('latitude', 'longitude', 'location_display', 'is_checked_in', 'last_location_update'),
            'classes': ('collapse',)
        }),
    )
    
    def employee_id(self, obj):
        return format_html('<strong style="color: #3b82f6;">{}</strong>', obj.E_id)
    employee_id.short_description = 'Employee ID'
    
    def name_display(self, obj):
        status = "🟢" if obj.is_checked_in else "⚫"
        return format_html('{} {}', status, obj.E_name)
    name_display.short_description = 'Name'
    
    def role_display(self, obj):
        if obj.is_manager:
            return format_html('<span style="background: rgba(34, 197, 94, 0.15); color: #86efac; padding: 4px 8px; border-radius: 4px;">Manager</span>')
        return format_html('<span style="background: rgba(59, 130, 246, 0.15); color: #93c5fd; padding: 4px 8px; border-radius: 4px;">Employee</span>')
    role_display.short_description = 'Role'
    
    def salary_type_display(self, obj):
        if obj.salary_type == 'monthly':
            return format_html('<span style="background: #e3f2fd; color: #1976d2; padding: 4px 8px; border-radius: 4px;">📅 Monthly</span>')
        return format_html('<span style="background: #fff3e0; color: #f57c00; padding: 4px 8px; border-radius: 4px;">⏰ Hourly</span>')
    salary_type_display.short_description = 'Salary Type'
    
    def rate_display(self, obj):
        if obj.salary_type == 'monthly':
            return format_html('<strong>₹{}/month</strong>', obj.monthly_salary)
        return format_html('<strong>₹{}/hr</strong>', obj.hourly_rate)
    rate_display.short_description = 'Rate'
    
    def location_display(self, obj):
        if obj.latitude and obj.longitude:
            status = "✅ Checked In" if obj.is_checked_in else "⏹️ Checked Out"
            return format_html(
                '<div style="background: var(--panel-2); padding: 8px; border-radius: 6px;">'
                '<div><strong>{}</strong></div>'
                '<div>📍 Lat: <strong>{}</strong></div>'
                '<div>📍 Lon: <strong>{}</strong></div>'
                '</div>',
                status, obj.latitude, obj.longitude
            )
        return "Not recorded"
    location_display.short_description = 'Location Status'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee_link', 'date_display', 'status_display', 'time_display', 'hours_display', 'checkout_type']
    list_filter = ['status', 'date', 'auto_checkout']
    search_fields = ['employee__E_name', 'employee__E_id']
    ordering = ['-date', '-check_in_time']
    readonly_fields = ['date', 'latitude', 'longitude', 'location_info', 'hours_worked_display', 'auto_checkout']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('📋 Attendance Information', {
            'fields': ('employee', 'date', 'status'),
        }),
        ('⏰ Time Tracking', {
            'fields': ('check_in_time', 'check_out_time', 'hours_worked_display', 'auto_checkout', 'checkout_reason'),
        }),
        ('⚙️ Manual Adjustment (HR Only)', {
            'fields': ('manual_hours', 'adjustment_reason'),
            'classes': ('collapse',)
        }),
        ('📍 Location Details', {
            'fields': ('latitude', 'longitude', 'location_info'),
            'classes': ('collapse',)
        }),
    )
    
    def employee_link(self, obj):
        return format_html('<strong style="color: #3b82f6;">{}</strong> ({})', obj.employee.E_name, obj.employee.E_id)
    employee_link.short_description = 'Employee'
    
    def date_display(self, obj):
        return format_html('<strong>{}</strong>', obj.date)
    date_display.short_description = 'Date'
    
    def status_display(self, obj):
        if obj.status == 'Present':
            return format_html('<span style="background: rgba(34, 197, 94, 0.15); color: #86efac; padding: 6px 12px; border-radius: 6px; font-weight: 600;">✅ Present</span>')
        else:
            return format_html('<span style="background: rgba(239, 68, 68, 0.15); color: #fca5a5; padding: 6px 12px; border-radius: 6px; font-weight: 600;">❌ Absent</span>')
    status_display.short_description = 'Status'
    
    def time_display(self, obj):
        if obj.check_in_time and obj.check_out_time:
            return format_html('In: {} | Out: {}', obj.check_in_time.strftime('%I:%M %p'), obj.check_out_time.strftime('%I:%M %p'))
        elif obj.check_in_time:
            return format_html('In: {} | <span style="color: #dc3545;">Not checked out</span>', obj.check_in_time.strftime('%I:%M %p'))
        return '-'
    time_display.short_description = 'Time'
    
    def hours_display(self, obj):
        hours = obj.hours_worked()
        if obj.manual_hours:
            return format_html('<span style="color: #ffc107;">⚙️ {} hrs (Manual)</span>', hours)
        return format_html('<strong>{} hrs</strong>', hours)
    hours_display.short_description = 'Hours'
    
    def checkout_type(self, obj):
        if obj.auto_checkout:
            return format_html('<span style="background: #ffc107; color: #000; padding: 4px 8px; border-radius: 4px;">🤖 Auto</span>')
        elif obj.check_out_time:
            return format_html('<span style="background: #28a745; color: #fff; padding: 4px 8px; border-radius: 4px;">✋ Manual</span>')
        return '-'
    checkout_type.short_description = 'Checkout Type'
    
    def location_info(self, obj):
        if obj.latitude and obj.longitude:
            return format_html(
                '<div style="background: var(--panel-2); padding: 8px; border-radius: 6px;">'
                '<div>📍 Latitude: <strong>{}</strong></div>'
                '<div>📍 Longitude: <strong>{}</strong></div>'
                '</div>',
                obj.latitude, obj.longitude
            )
        return "Not recorded"
    location_info.short_description = 'Location Details'
    
    def hours_worked_display(self, obj):
        return f"{obj.hours_worked()} hours"
    hours_worked_display.short_description = 'Calculated Hours'


@admin.register(SalaryAdjustment)
class SalaryAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'month_year', 'calculated_display', 'adjusted_display', 'difference', 'adjusted_by', 'adjusted_on']
    list_filter = ['year', 'month', 'adjusted_by']
    search_fields = ['employee__E_name', 'employee__E_id']
    readonly_fields = ['adjusted_by', 'adjusted_on']
    
    fieldsets = (
        ('Employee Information', {
            'fields': ('employee', 'month', 'year'),
        }),
        ('Salary Details', {
            'fields': ('calculated_salary', 'adjusted_salary', 'adjustment_reason'),
        }),
        ('Audit Information', {
            'fields': ('adjusted_by', 'adjusted_on'),
        }),
    )
    
    def month_year(self, obj):
        return f"{obj.month}/{obj.year}"
    month_year.short_description = 'Period'
    
    def calculated_display(self, obj):
        return format_html('<strong>₹{}</strong>', obj.calculated_salary)
    calculated_display.short_description = 'Calculated'
    
    def adjusted_display(self, obj):
        return format_html('<strong style="color: #28a745;">₹{}</strong>', obj.adjusted_salary)
    adjusted_display.short_description = 'Final Salary'
    
    def difference(self, obj):
        diff = obj.adjusted_salary - obj.calculated_salary
        color = '#28a745' if diff > 0 else '#dc3545' if diff < 0 else '#6c757d'
        symbol = '+' if diff > 0 else ''
        return format_html('<strong style="color: {};">{}₹{}</strong>', color, symbol, abs(diff))
    difference.short_description = 'Difference'


class CustomAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('CSS_file/admin_custom.css',)
        }
