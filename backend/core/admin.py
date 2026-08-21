from django.contrib import admin
from .models import TechnicianNotification, customer_signup, Technician_signup, ServiceRequest, ServiceDetail, ServiceAddress, Service





@admin.register(customer_signup)
class CustomerSignupAdmin(admin.ModelAdmin):
    list_display = ['get_username', 'get_email', 'contact', 'get_password_status']
    search_fields = ['user__username', 'user__email', 'contact']
    readonly_fields = ['get_username', 'get_email', 'get_password_status']
    fields = ['user', 'contact', 'get_username', 'get_email', 'get_password_status']

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def get_password_status(self, obj):
        return '✓ Set' if obj.user.password else '✗ Not Set'
    get_password_status.short_description = 'Password'


@admin.register(Technician_signup)
class TechnicianSignupAdmin(admin.ModelAdmin):
    list_display = ['get_username', 'get_email', 'contact', 'is_available', 'get_password_status']
    search_fields = ['user__username', 'user__email', 'contact']
    list_filter = ['is_available']
    readonly_fields = ['get_username', 'get_email', 'get_password_status']
    fields = ['user', 'contact', 'is_available', 'get_username', 'get_email', 'get_password_status']

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def get_password_status(self, obj):
        return '✓ Set' if obj.user.password else '✗ Not Set'
    get_password_status.short_description = 'Password'


@admin.register(ServiceDetail)
class ServiceDetailAdmin(admin.ModelAdmin):
    list_display = ['id', 'service_category', 'priority', 'preferred_service_date', 'created_at']
    search_fields = ['service_category']
    list_filter = ['priority', 'created_at']


@admin.register(ServiceAddress)
class ServiceAddressAdmin(admin.ModelAdmin):
    list_display = ['id', 'house_flat_no', 'city', 'pincode', 'created_at']
    search_fields = ['city', 'street_area', 'pincode']
    list_filter = ['city', 'created_at']


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_username', 'technician_username', 'get_service_type', 'status', 'created_at']
    search_fields = ['customer_username', 'technician_username', 'service_detail__service_category', 'service_address__city']
    list_filter = ['status', 'created_at']
    list_editable = ['technician_username', 'status']
    readonly_fields = ['created_at', 'updated_at', 'customer_username', 'get_available_technicians']
    fields = ['customer_username', 'technician_username', 'service_detail', 'service_address', 'status', 'get_available_technicians', 'created_at', 'updated_at']

    def get_service_type(self, obj):
        return obj.service_detail.service_category
    get_service_type.short_description = 'Service Type'
    
    def get_available_technicians(self, obj):
        technicians = Technician_signup.objects.values_list('username', flat=True)
        tech_list = ', '.join(technicians)
        return f"Available: {tech_list if tech_list else 'No technicians registered'}"
    get_available_technicians.short_description = 'Available Technicians (Type username above)'

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_enabled']
    list_editable = ['is_enabled']   # 🔥 toggle ON/OFF directly
    search_fields = ['name']
    list_filter = ['is_enabled']

@admin.register(TechnicianNotification)
class TechnicianNotificationAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'technician',
        'title',
        'is_read',
        'created_at'
    ]

    list_filter = ['is_read', 'created_at']

    search_fields = [
        'technician__username',
        'title'
    ]
    