from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Attendance

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'name_display', 'role_display', 'salary_display']
    list_filter = ['is_manager', 'user__date_joined']
    search_fields = ['E_id', 'E_name']
    ordering = ['-id']
    readonly_fields = ['latitude', 'longitude', 'location_display']
    
    fieldsets = (
        ('👤 Basic Information', {
            'fields': ('user', 'E_id', 'E_name'),
            'classes': ('wide',)
        }),
        ('💼 Employment Details', {
            'fields': ('salary', 'is_manager'),
        }),
        ('📍 Location Information', {
            'fields': ('latitude', 'longitude', 'location_display'),
            'classes': ('collapse',)
        }),
    )
    
    def employee_id(self, obj):
        return format_html('<strong style="color: #3b82f6;">{}</strong>', obj.E_id)
    employee_id.short_description = 'Employee ID'
    
    def name_display(self, obj):
        return obj.E_name
    name_display.short_description = 'Name'
    
    def role_display(self, obj):
        if obj.is_manager:
            return format_html('<span style="background: rgba(34, 197, 94, 0.15); color: #86efac; padding: 4px 8px; border-radius: 4px;">Manager</span>')
        return format_html('<span style="background: rgba(59, 130, 246, 0.15); color: #93c5fd; padding: 4px 8px; border-radius: 4px;">Employee</span>')
    role_display.short_description = 'Role'
    
    def salary_display(self, obj):
        return format_html('<strong>₹{}</strong>', obj.salary)
    salary_display.short_description = 'Salary'
    
    def location_display(self, obj):
        if obj.latitude and obj.longitude:
            return format_html(
                '<div style="background: var(--panel-2); padding: 8px; border-radius: 6px;">'
                '<div>📍 Latitude: <strong>{}</strong></div>'
                '<div>📍 Longitude: <strong>{}</strong></div>'
                '</div>',
                obj.latitude, obj.longitude
            )
        return "Not recorded"
    location_display.short_description = 'Last Location'

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee_link', 'date_display', 'status_display']
    list_filter = ['status', 'date']
    search_fields = ['employee__E_name', 'employee__E_id']
    ordering = ['-date']
    readonly_fields = ['date', 'latitude', 'longitude', 'location_info']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('📋 Attendance Information', {
            'fields': ('employee', 'date', 'status'),
        }),
        ('📍 Location Details', {
            'fields': ('latitude', 'longitude', 'location_info'),
            'classes': ('collapse',)
        }),
    )
    
    def employee_link(self, obj):
        return format_html(
            '<strong style="color: #3b82f6;">{}</strong> ({})',
            obj.employee.E_name, obj.employee.E_id
        )
    employee_link.short_description = 'Employee'
    
    def date_display(self, obj):
        return format_html('<strong>{}</strong>', obj.date)
    date_display.short_description = 'Date'
    
    def status_display(self, obj):
        if obj.status == 'Present':
            return format_html(
                '<span style="background: rgba(34, 197, 94, 0.15); color: #86efac; padding: 6px 12px; border-radius: 6px; font-weight: 600;">✅ Present</span>'
            )
        else:
            return format_html(
                '<span style="background: rgba(239, 68, 68, 0.15); color: #fca5a5; padding: 6px 12px; border-radius: 6px; font-weight: 600;">❌ Absent</span>'
            )
    status_display.short_description = 'Status'
    
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
