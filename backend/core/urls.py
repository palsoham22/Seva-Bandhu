from django.urls import path
from . import views

# 🔥 ADD THESE
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.loader, name='loader'),
    path('home/', views.home, name='home'),
    path('base/', views.base, name='base'),

    # Technician
    path('technician/dashboard_t/', views.technician_dashboard, name='technician_dashboard'),
    path('technician/my_job/', views.technician_my_jobs, name='technician_my_jobs'),
    path('technician/update_location/', views.technician_update_location, name='technician_update_location'),
    path('technician/update_status/', views.technician_update_status, name='technician_update_status'),
    path('technician/accept-request/<int:id>/', views.accept_request, name='accept_request'),
    path('technician/signup/', views.technician_sign_up, name='technician_signup'),
    path('technician/login/', views.technician_login, name='technician_login'),
    path('technician/logout/', views.technician_logout, name='technician_logout'),
    path('technician/complete_profile/', views.technician_complete_profile, name='technician_complete_profile'),
    path('technician/dismiss-notification/<int:id>/',views.dismiss_notification,name='dismiss_notification'),
    path('technician/navigation/<int:id>/',views.technician_navigation,name='technician_navigation'
),

    # Customer
    path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('customer/create_request/', views.customer_create_request, name='customer_create_request'),
    path('customer/my_requests/', views.customer_my_requests, name='customer_my_requests'),
    path('payment/<int:service_id>/', views.payment_page, name='payment_page'),
    path('invoice/<int:service_id>/', views.invoice_pdf, name='invoice_pdf'),
    path('customer/track_request/', views.customer_track_request, name='customer_track_request'),
    path('customer/phone-verification/', views.customer_phone_verification, name='customer_phone_verification'),
    path('customer/signup/', views.customer_sign_up, name='customer_signup'),
    path('customer/login/', views.customer_login, name='customer_login'),
    path('customer/logout/', views.customer_logout, name='customer_logout'),
    path('customer/service-selection/', views.service_selection, name='service_selection'),
    path('technician/start-tracking/<int:id>/', views.start_tracking, name='start_tracking'),
    path('customer/tracking/<int:id>/', views.customer_tracking, name='customer_tracking'),
    path('customer/google-auth/',views.customer_google_auth,name='customer_google_auth'),
    path('customer/signup/send-otp/', views.send_signup_otp, name='send_signup_otp'),
    path('customer/signup/verify-otp/', views.verify_signup_otp, name='verify_signup_otp'),
    path('customer/phone-verify-complete/', views.customer_phone_verify_complete, name='customer_phone_verify_complete'),
]

# 🔥 VERY IMPORTANT — SERVE IMAGES
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
