from django.db import models
from django.contrib.auth.models import User


class customer_signup(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    email = models.EmailField()
    contact = models.CharField(max_length=15)
    password = models.CharField(max_length=128)
    email_verified = models.BooleanField(
    default=False
)
    phone_verified = models.BooleanField(
        default=False
    )

    verification_token = models.CharField(
    max_length=200,
    blank=True,
    null=True
)

    class Meta:
        db_table = 'customer_signup'

    def __str__(self):
        return self.username


class Technician_signup(models.Model):
    SERVICE_CATEGORIES = [
        ('AC Service', 'AC Service'),
        ('Electrician', 'Electrician'),
        ('Washing Machine Service', 'Washing Machine Service'),
        ('Plumbing', 'Plumbing'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    email = models.EmailField()
    contact = models.CharField(max_length=15)
    password = models.CharField(max_length=128)
    is_available = models.BooleanField(default=True)
    
    # Profile completion fields
    service_category = models.CharField(max_length=100, choices=SERVICE_CATEGORIES, blank=True, null=True)
    years_of_experience = models.IntegerField(blank=True, null=True)
    working_locations = models.CharField(max_length=500, blank=True, null=True)  # Comma-separated cities
    profile_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'Technician_signup'

    def __str__(self):
        return self.username


class ServiceAddress(models.Model):
    house_flat_no = models.CharField(max_length=50)
    street_area = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    additional_landmark = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ServiceAddress'

    def __str__(self):
        return f"{self.house_flat_no}, {self.street_area}, {self.city}"


class ServiceDetail(models.Model):
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Emergency', 'Emergency'),
    ]

    service_category = models.CharField(max_length=100)
    problem_description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    preferred_service_date = models.DateField()
    preferred_time_slot = models.CharField(max_length=50)
    contact_number = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ServiceDetail'

    def __str__(self):
        return f"{self.service_category} - {self.priority}"


class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending - No Technician Assigned'),
        ('Assigned', 'Assigned - Technician Assigned'),
        ('In Progress', 'In Progress - Work Started'),
        ('Completed', 'Completed - Work Done'),
    ]

    customer_username = models.CharField(max_length=100)
    technician_username = models.CharField(max_length=100, blank=True, null=True)
    
    # Foreign keys to separate detail tables
    service_detail = models.ForeignKey(ServiceDetail, on_delete=models.CASCADE, related_name='requests')
    service_address = models.ForeignKey(ServiceAddress, on_delete=models.CASCADE, related_name='requests')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tracking_active = models.BooleanField(default=False)
    
    customer_latitude = models.FloatField(
        null=True,
        blank=True
    )

    customer_longitude = models.FloatField(
        null=True,
        blank=True
    )

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]

    PAYMENT_METHOD = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]

    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def customer(self):
        return customer_signup.objects.filter(username=self.customer_username).select_related('user').first()

    @property
    def technician(self):
        if not self.technician_username:
            return None
        return Technician_signup.objects.filter(username=self.technician_username).select_related('user').first()

    class Meta:
        db_table = 'ServiceRequest'

    def __str__(self):
        return f"REQ-{self.id} - {self.customer_username}"
        


class Service(models.Model):
     name = models.CharField(max_length=100, unique=True)
     image=models.ImageField(upload_to='service_images/' , blank=True, null=True)  # ✅ Add image field
     price = models.IntegerField(default=0)
     is_enabled = models.BooleanField(default=True)  # ✅ Admin control

     class Meta:
        db_table = 'Service'

     def __str__(self):
        return self.name

class TechnicianNotification(models.Model):

    technician = models.ForeignKey(
        Technician_signup,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.technician.username} - {self.title}"      