from io import BytesIO
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.template.loader import get_template
from django.urls import reverse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.views.decorators.csrf import csrf_exempt
from xhtml2pdf import pisa
import json
import random
import uuid

from .models import (
    TechnicianNotification,
    customer_signup,
    Technician_signup,
    ServiceRequest,
    ServiceDetail,
    ServiceAddress,
    Service,
)

def home(request):
    return render(request, 'home.html')


def loader(request):
    return render(request, 'customer/loader.html')


def base(request):
    return render(request, 'base.html')


def technician_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('technician_login')
    
    try:
        # ✅ FIX: always fetch technician using username (same as assignment logic)
        technician = Technician_signup.objects.filter(
            username__iexact=request.user.username.strip()
        ).first()

        if not technician:
            print("❌ Technician not found for:", request.user.username)
            return redirect('technician_login')

    except Exception as e:
        print("❌ ERROR:", str(e))
        return redirect('technician_login')
    
    # ✅ Fetch only jobs assigned to THIS technician
    assigned_jobs = ServiceRequest.objects.filter(
        technician_username__iexact=technician.username
    ).order_by('-created_at')
    
    # ✅ Correct job counts
    total_jobs = assigned_jobs.count()
    assigned_jobs_count = assigned_jobs.filter(status='Assigned').count()
    in_progress_jobs = assigned_jobs.filter(status='In Progress').count()
    completed_jobs = assigned_jobs.filter(status='Completed').count()
    # 🔔 Pending notifications
    notifications = TechnicianNotification.objects.filter(
    technician=technician,
    is_read=False
)
    context = {
        'technician': technician,
        'assigned_jobs': assigned_jobs,
        'total_jobs': total_jobs,
        'pending_jobs': assigned_jobs_count,
        'in_progress_jobs': in_progress_jobs,
        'completed_jobs': completed_jobs,
        'notifications': notifications
    }
    
    return render(request, 'technician/dashboard_t.html', context)

def technician_my_jobs(request):
    if not request.user.is_authenticated:
        return redirect('technician_login')
    
    try:
        technician = Technician_signup.objects.get(user=request.user)
    except Technician_signup.DoesNotExist:
        return render(request, 'technician/my_job.html', {
            'error': 'Technician profile not found.'
        })
    
    # Fetch all jobs assigned to this technician
    assigned_jobs = ServiceRequest.objects.filter(
        technician_username=technician.username
    ).select_related('service_detail', 'service_address').order_by('-created_at')
    
    context = {
        'technician': technician,
        'my_jobs': assigned_jobs,
    }
    
    return render(request, 'technician/my_job.html', context)


def technician_update_location(request):
    return render(request, 'technician/update_location.html')


def technician_update_status(request):
    if not request.user.is_authenticated:
        return redirect('technician_login')
    
    try:
        technician = Technician_signup.objects.get(user=request.user)
    except Technician_signup.DoesNotExist:
        return render(request, 'technician/update_status.html', {
            'error': 'Technician profile not found.'
        })
    
    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        new_status = request.POST.get('status')
        
        try:
            job = ServiceRequest.objects.get(
                id=job_id,
                technician_username=technician.username
            )

            # 🔥 UPDATE JOB STATUS
            job.status = new_status
            job.save()

            # 🔥 MAIN FIX — HANDLE AVAILABILITY
            if new_status == "Completed":
                if job.payment_method == 'offline' and job.payment_status == 'pending':
                    job.payment_status = 'paid'
                    job.save()
                    try:
                        send_invoice_email(job)
                    except Exception as e:
                        print("❌ Invoice email failed:", str(e))

                technician.is_available = True
                technician.save()
                print("✅ Technician is now AVAILABLE")

            elif new_status == "In Progress":
                technician.is_available = False
                technician.save()
                print("🔒 Technician marked BUSY")

            return redirect('technician_my_jobs')

        except ServiceRequest.DoesNotExist:
            return render(request, 'technician/update_status.html', {
                'technician': technician,
                'error': 'Job not found.'
            })
    
    # Fetch all jobs assigned to this technician
    assigned_jobs = ServiceRequest.objects.filter(
        technician_username=technician.username
    ).select_related('service_detail', 'service_address').order_by('-created_at')
    
    context = {
        'technician': technician,
        'my_jobs': assigned_jobs,
    }
    
    return render(request, 'technician/update_status.html', context)


def technician_sign_up(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        contact = request.POST.get('contact')
        password = request.POST.get('password')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return render(request, 'technician/signup.html', {
                'error': 'Username already exists. Please choose a different one.'
            })

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return render(request, 'technician/signup.html', {
                'error': 'Email already registered. Please use a different email or login.'
            })

        try:
            # Create Django user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Create technician profile with all fields
            Technician_signup.objects.create(
                user=user,
                username=username,
                email=email,
                contact=contact,
                password=password
            )

            return redirect('technician_login')
        
        except Exception as e:
            return render(request, 'technician/signup.html', {
                'error': f'An error occurred: {str(e)}'
            })

    return render(request, 'technician/signup.html')


def technician_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            logout(request)  # ✅ CLEAR OLD SESSION
            login(request, user)
            request.session.save()  # ✅ FORCE SAVE

            return redirect('technician_dashboard')

        else:
            return render(request, 'technician/login.html', {
                'error': 'Invalid username or password. Please try again.'
            })

    return render(request, 'technician/login.html')


def technician_logout(request):
    logout(request)
    return redirect('technician_login')


from .models import Service  # 🔥 IMPORTANT

def technician_complete_profile(request):
    if not request.user.is_authenticated:
        return redirect('technician_login')
    
    try:
        technician = Technician_signup.objects.get(user=request.user)
    except Technician_signup.DoesNotExist:
        return render(request, 'technician/complete_profile.html', {
            'error': 'Technician profile not found.'
        })
    
    # 🔥 GET SERVICES FROM DB (MAIN FIX)
    services = Service.objects.filter(is_enabled=True)

    if request.method == "POST":
        try:
            service_category = request.POST.get('service_category')
            years_of_experience = request.POST.get('years_of_experience')
            working_locations = request.POST.get('working_locations')
            
            technician.service_category = service_category
            technician.years_of_experience = int(years_of_experience)
            technician.working_locations = working_locations
            technician.profile_completed = True
            technician.save()
            
            return redirect('technician_dashboard')
        
        except Exception as e:
            return render(request, 'technician/complete_profile.html', {
                'technician': technician,
                'services': services,  # 🔥 KEEP THIS
                'error': f'Error updating profile: {str(e)}'
            })
    
    # 🔥 FINAL CONTEXT (FIXED)
    context = {
        'technician': technician,
        'services': services   # ✅ NEW SYSTEM
    }
    
    return render(request, 'technician/complete_profile.html', context)


def customer_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('customer_login')
    
    try:
        # Get the current customer profile
        customer = customer_signup.objects.filter(user=request.user).first()

        if not customer:
           return redirect('customer_login')
    except customer_signup.DoesNotExist:
        return render(request, 'customer/create_request', {
            'error': 'Customer profile not found. Please complete your signup.'
        })
    
    # Get all service requests for this customer
    service_requests = ServiceRequest.objects.filter(customer_username=customer.username).order_by('-created_at')
    
    # Enrich service requests with technician information
    requests_with_technicians = []
    technicians_list = []
    
    for service_request in service_requests:
        request_data = {
            'request': service_request,
            'technician': None
        }
        
        # If technician is assigned, fetch technician details
        if service_request.technician_username:
            try:
                technician = Technician_signup.objects.get(username=service_request.technician_username)
                request_data['technician'] = technician
                
                # Collect unique technicians
                if technician not in technicians_list:
                    technicians_list.append(technician)
            except Technician_signup.DoesNotExist:
                pass
        
        requests_with_technicians.append(request_data)
    
    # Calculate statistics
    total_requests = service_requests.count()
    pending_requests = service_requests.filter(status='Pending').count()
    in_progress_requests = service_requests.filter(status='In Progress').count()
    completed_requests = service_requests.filter(status='Completed').count()
    
    # Get recent requests (last 5)
    recent_requests = requests_with_technicians[:5]
    
    context = {
        'customer': customer,
        'service_requests': recent_requests,
        'technicians': technicians_list,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'in_progress_requests': in_progress_requests,
        'completed_requests': completed_requests,
    }
    
    return render(request, 'customer/dashboard_c.html', context)


def customer_create_request(request):
    if not request.user.is_authenticated:
        return redirect('customer_login')
    selected_service = request.GET.get('service', '')
    try:
        customer = customer_signup.objects.filter(user=request.user).first()

        if not customer:
            return redirect('customer_login')
    except customer_signup.DoesNotExist:
        return render(request, 'customer/create_request.html', {
            'error': 'Customer profile not found.'
        })   
    
    if request.method == "POST":
        try:
            # Get form data for ServiceDetail
            service_category = request.POST.get('service_category')
            problem_description = request.POST.get('problem_description')
            priority = request.POST.get('priority')
            preferred_service_date = request.POST.get('preferred_service_date')
            preferred_time_slot = request.POST.get('preferred_time_slot')
            contact_number = request.POST.get('contact_number')

            payment_method = request.POST.get('payment_method')
            if payment_method not in ['online', 'offline']:
                raise ValueError('Please select a valid payment method.')
            
            # Get form data for ServiceAddress
            house_flat_no = request.POST.get('house_flat_no')
            street_area = request.POST.get('street_area')
            city = request.POST.get('city')
            pincode = request.POST.get('pincode')
            additional_landmark = request.POST.get('additional_landmark')

            customer_latitude = request.POST.get('customer_latitude') or None
            customer_longitude = request.POST.get('customer_longitude') or None
            
            # Create ServiceDetail
            service_detail = ServiceDetail.objects.create(
                service_category=service_category,
                problem_description=problem_description,
                priority=priority,
                preferred_service_date=preferred_service_date,
                preferred_time_slot=preferred_time_slot,
                contact_number=contact_number
            )
            
            # Create ServiceAddress
            service_address = ServiceAddress.objects.create(
                house_flat_no=house_flat_no,
                street_area=street_area,
                city=city,
                pincode=pincode,
                additional_landmark=additional_landmark
            )

            matched_service = Service.objects.filter(name__iexact=service_category).first()
            amount = matched_service.price if matched_service else 0
            
            # Create ServiceRequest
            service_request = ServiceRequest.objects.create(
                customer_username=customer.username,
                service_detail=service_detail,
                service_address=service_address,
                customer_latitude=customer_latitude,
                customer_longitude=customer_longitude,
                status='Pending',
                payment_method=payment_method,
                payment_status='pending',
                amount=amount
            )
            # 🔥 CREATE NOTIFICATIONS FOR MATCHING TECHNICIANS
            matching_technicians = Technician_signup.objects.filter(
                service_category__iexact=service_detail.service_category
            )

            for technician in matching_technicians:
                TechnicianNotification.objects.create(
                    technician=technician,
                    service_request=service_request,
                    title=f"New {service_detail.service_category} Request",
                    message=f"{service_address.city} | {service_detail.preferred_time_slot}"
                )

            # Broadcast new request to connected technicians
            channel_layer = get_channel_layer()
            print("🔥 BROADCASTING NEW REQUEST")
            async_to_sync(channel_layer.group_send)(
                'technicians',   # keep same group if you are using it
                {
                    'type': 'new_request',
                    'content': {
                        'type': 'new_request',
                        'request_id': service_request.id,
                        'service_category': service_detail.service_category,
                        'city': service_address.city,
                        'priority': service_detail.priority,
                        'problem_description': service_detail.problem_description,
                        'preferred_date': str(service_detail.preferred_service_date),
                        'preferred_time': service_detail.preferred_time_slot,
                        'address': service_address.street_area,
                    }
                }
            )

            print(f"✅ New service request created and broadcasted: ID {service_request.id}")
            if payment_method == 'online':
                return redirect('payment_page', service_id=service_request.id)

            return redirect('customer_my_requests')
        
        except Exception as e:
            return render(request, 'customer/create_request.html', {
                'customer': customer,
                'error': f'Error creating request: {str(e)}'
            })
    return render(request, 'customer/create_request.html', {
        'customer': customer,
        'selected_service': selected_service
    })


def customer_my_requests(request):
    if not request.user.is_authenticated:
        return redirect('customer_login')
    
    try:
        customer = customer_signup.objects.filter(user=request.user).first()

        if not customer:
          return redirect('customer_login')
    except customer_signup.DoesNotExist:
        return render(request, 'customer/my_requests.html', {
            'error': 'Customer profile not found.'
        })
    
    # Get all service requests for this customer with related ServiceDetail
    service_requests = ServiceRequest.objects.filter(
        customer_username=customer.username
    ).select_related('service_detail', 'service_address').order_by('-created_at')
    
    # Fetch technician details for all requests with assigned technician
    requests_with_technician = []
    for req in service_requests:
        technician = None
        if req.technician_username:  # Fetch technician for ANY status if one is assigned
            try:
                technician = Technician_signup.objects.get(username=req.technician_username)
            except Technician_signup.DoesNotExist:
                technician = None
        # Create a dict with request and technician data
        requests_with_technician.append({
            'request': req,
            'technician': technician,
        })
    
    context = {
        'customer': customer,
        'service_requests': requests_with_technician,
    }
    
    return render(request, 'customer/my_requests.html', context)


def customer_track_request(request):
    return render(request, 'customer/tracking.html')


def customer_phone_verification(request):
    # Determine which user this verification is for: session or logged-in
    pending_user_id = request.session.get('pending_phone_user')

    phone_number = ''

    if pending_user_id:
        try:
            pending_user = User.objects.filter(id=pending_user_id).first()
            if pending_user:
                cust = customer_signup.objects.filter(user=pending_user).first()
                if cust and cust.contact:
                    phone_number = cust.contact
        except Exception:
            phone_number = ''

    elif request.user.is_authenticated:
        cust = customer_signup.objects.filter(user=request.user).first()
        if cust and cust.contact:
            phone_number = cust.contact

    else:
        # No context for phone verification, redirect to signup
        return redirect('customer_signup')

    return render(request, 'customer/phone_verification.html', {
        'phone_number': phone_number,
        'pending_phone_user': pending_user_id
    })


def customer_sign_up(request):

    verified_email = request.session.get(
        'verified_email'
    )

    if request.method == "POST":

        username = request.POST.get(
            'username'
        )

        email = request.POST.get(
            'email'
        )

        contact = request.POST.get(
            'contact'
        )

        password = request.POST.get(
            'password'
        )

        #################################################
        # EMAIL MUST BE VERIFIED
        #################################################

        if not verified_email or verified_email != email:

            return render(

                request,

                'customer/signup.html',

                {

                    'error':
                    'Please verify this email before signing up.',

                    'verified_email':
                    verified_email

                }

            )

        #################################################
        # USERNAME EXISTS
        #################################################

        if User.objects.filter(
            username=username
        ).exists():

            return render(

                request,

                'customer/signup.html',

                {

                    'error':
                    'Username already exists.',

                    'verified_email':
                    verified_email

                }

            )

        #################################################
        # EMAIL EXISTS
        #################################################

        if User.objects.filter(
            email=email
        ).exists():

            return render(

                request,

                'customer/signup.html',

                {

                    'error':
                    'Email already registered.',

                    'verified_email':
                    verified_email

                }

            )

        try:

            #################################################
            # CREATE DJANGO USER
            #################################################

            user = User.objects.create_user(

                username=username,

                email=email,

                password=password

            )

            #################################################
            # CREATE CUSTOMER
            #################################################

            customer_signup.objects.create(

                user=user,

                username=username,

                email=email,

                contact=contact,

                password=password,

                email_verified=True,

                phone_verified=False

            )

            #################################################
            # SAVE USER SESSION
            #################################################

            request.session[
                'pending_phone_user'
            ] = user.id

            #################################################
            # CLEAN EMAIL SESSIONS
            #################################################

            request.session.pop(
                'verified_email',
                None
            )

            request.session.pop(
                'email_verification_token',
                None
            )

            request.session.pop(
                'email_to_verify',
                None
            )

            #################################################
            # REDIRECT PHONE VERIFICATION
            #################################################

            return redirect(
                     '/customer/phone-verification/'
)
    

        except Exception as e:

            return render(

                request,

                'customer/signup.html',

                {

                    'error':
                    f'An error occurred: {str(e)}',

                    'verified_email':
                    verified_email

                }

            )

    return render(

        request,

        'customer/signup.html',

        {

            'verified_email':
            verified_email

        }

    )


def customer_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Check email verification status if a customer profile exists
            try:
                customer = customer_signup.objects.get(user=user)
            except customer_signup.DoesNotExist:
                customer = None

            if customer and not customer.email_verified and customer.verification_token:
                return render(request, 'customer/login.html', {
                    'error': 'Please verify your email first.'
                })

            # Log the user in
            login(request, user)
            customer_signup.objects.get_or_create(user=user)
            return redirect('service_selection')
        else:
            return render(request, 'customer/login.html', {
                'error': 'Invalid username or password. Please try again.'
            })

    return render(request, 'customer/login.html')


def customer_logout(request):
    logout(request)
    return redirect('customer_login')


from .models import Service

def service_selection(request):

    services = Service.objects.all()

    service_list = []

    for service in services:
        # 🔥 check if technician available
        available = Technician_signup.objects.filter(
            service_category__iexact=service.name,
            is_available=True
        ).exists()

        # 🔥 final decision
        is_active = service.is_enabled and available

        service_list.append({
            'name': service.name,
            'image': service.image,
            'price': service.price,
            'is_active': is_active
        })

    return render(request, 'customer/service_selection.html', {
        'services': service_list
    })




from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

@csrf_exempt
def accept_request(request, id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'})

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'})

    try:
        technician = Technician_signup.objects.get(user=request.user)
    except Technician_signup.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Technician profile not found'})

    with transaction.atomic():
        # Lock technician row (prevents race conditions)
        technician = Technician_signup.objects.select_for_update().get(id=technician.id)

        service_request = get_object_or_404(ServiceRequest, id=id)

        # 🔥 BLOCK if request already taken
        if service_request.status != 'Pending':
            return JsonResponse({'status': 'failed', 'message': 'Already taken'})

        # 🔥 TIME CONFLICT CHECK (MAIN FIX)
        conflict = ServiceRequest.objects.filter(
            technician_username=technician.username,
            service_detail__preferred_service_date=service_request.service_detail.preferred_service_date,
            service_detail__preferred_time_slot=service_request.service_detail.preferred_time_slot,
            status__in=['Assigned', 'In Progress']
        ).exists()

        if conflict:
            return JsonResponse({
                'status': 'failed',
                'message': 'You already have a job at this date & time'
            })

        # (Optional) Keep this if you still want global busy flag
        

        # 🔥 ASSIGN JOB
        service_request.technician_username = technician.username
        service_request.status = 'Assigned'
        service_request.save()

        # 🔒 mark busy (optional if you keep global flag)
        technician.is_available = False
        technician.save()

        # 🔥 MARK NOTIFICATIONS AS READ
        TechnicianNotification.objects.filter(
            service_request=service_request
        ).update(is_read=True)

        # 🔥 REALTIME REMOVE NOTIFICATION
        channel_layer = get_channel_layer()

        print("🔥 SENDING notification_removed EVENT")

        async_to_sync(channel_layer.group_send)(
            'technicians',
            {
                'type': 'notification_removed',
                'request_id': service_request.id,
            }
        )

    return JsonResponse({'status': 'success'})

def dismiss_notification(request, id):

    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error'
        })

    try:

        notification = TechnicianNotification.objects.get(id=id)

        notification.is_read = True
        notification.save()

        return JsonResponse({
            'status': 'success'
        })

    except TechnicianNotification.DoesNotExist:

        return JsonResponse({
            'status': 'error'
        })
def customer_tracking(request, id):
    if not request.user.is_authenticated:
        return redirect('customer_login')

    customer = customer_signup.objects.filter(user=request.user).first()
    if not customer:
        return redirect('customer_login')

    service_request = get_object_or_404(
        ServiceRequest,
        id=id,
        customer_username=customer.username
    )

    return render(request, 'customer/tracking.html', {
        'service_request': service_request
    })
def start_tracking(request, id):

    service_request = get_object_or_404(
        ServiceRequest,
        id=id
    )

    service_request.tracking_active = True

    service_request.save()

    return JsonResponse({
        'status': 'success'
    })


def generate_invoice_pdf(service):
    print('📄 generate_invoice_pdf called for service:', service.id)
    template = get_template('customer/invoice.html')
    html = template.render({'service': service})
    result = BytesIO()
    pdf_status = pisa.CreatePDF(src=html, dest=result)

    if pdf_status.err:
        print('❌ PDF generation failed for service:', service.id, 'errors:', pdf_status.err)
        return None

    return result.getvalue()


def send_invoice_email(service):
    print('✉️ send_invoice_email called for service:', service.id)
    customer = getattr(service, 'customer', None)
    if not customer or not hasattr(customer, 'user'):
        print('❌ Unable to resolve customer user for service:', service.id)
        return False

    recipient_email = customer.user.email
    if not recipient_email:
        print('❌ No recipient email for service:', service.id)
        return False

    pdf_bytes = generate_invoice_pdf(service)
    if not pdf_bytes:
        print('❌ PDF generation returned no bytes for service:', service.id)
        return False

    subject = f"Seva Bandhu Invoice - Service Request #{service.id}"
    body = (
        f"Hello {customer.user.username},\n\n"
        f"Thank you for completing the payment for your service request #{service.id}. "
        f"Your invoice is attached to this email.\n\n"
        "Best regards,\nSeva Bandhu Team"
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@seva-bandhu.local')

    email_message = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[recipient_email],
    )
    email_message.attach(f'invoice_{service.id}.pdf', pdf_bytes, 'application/pdf')
    email_message.send(fail_silently=False)

    print('✅ Invoice email sent to:', recipient_email)
    return True


def payment_page(request, service_id):
    service_request = get_object_or_404(ServiceRequest, id=service_id)

    if not request.user.is_authenticated or request.user.username != service_request.customer_username:
        return redirect('customer_login')

    if request.method == "POST":
        print('🔔 payment_page POST request triggered for service:', service_request.id)
        if service_request.payment_method != 'online':
            return HttpResponseForbidden('Only online payments can be processed here.')

        service_request.payment_status = 'paid'
        service_request.save()

        print('🔔 payment status updated to paid for service:', service_request.id)
        try:
            send_invoice_email(service_request)
        except Exception as e:
            print('❌ Invoice email error:', str(e))

        return redirect('customer_dashboard')

    return render(request, 'customer/payment.html', {
        'service_request': service_request
    })


def invoice_pdf(request, service_id):
    service_request = get_object_or_404(ServiceRequest, id=service_id)

    if not request.user.is_authenticated or request.user.username != service_request.customer_username:
        return HttpResponseForbidden('Not authorized to download this invoice.')

    pdf_bytes = generate_invoice_pdf(service_request)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{service_request.id}.pdf"'
    return response

def technician_navigation(request, id):

    service_request = ServiceRequest.objects.get(id=id)

    return render(

        request,

        'technician/navigation.html',

        {

            'service_request': service_request

        }
    )


def customer_google_auth(request):

    if request.method == "POST":

        data = json.loads(request.body)

        email = data.get("email")

        name = data.get("name")

        ###################################################
        # CHECK USER
        ###################################################

        user = User.objects.filter(
            email=email
        ).first()

        ###################################################
        # CREATE USER IF NOT EXISTS
        ###################################################

        if not user:

            username = email.split("@")[0] + str(
                random.randint(1000,9999)
            )

            password = User.objects.make_random_password()

            user = User.objects.create_user(

                username=username,

                email=email,

                password=password

            )

            customer_signup.objects.create(

                user=user,

                username=username,

                email=email,

                contact="Google User",

                password=password

            )

        ###################################################
        # LOGIN USER
        ###################################################

        login(request, user)

        return JsonResponse({

            "status": "success"

        })

    return JsonResponse({

        "status": "failed"

    })
def verify_email(request, token):

    saved_token = request.session.get(
        'email_verification_token'
    )

    email = request.session.get(
        'email_to_verify'
    )

    if token == saved_token and email:

        request.session[
            'verified_email'
        ] = email

        request.session.save()

        return redirect(
            '/customer/signup/'
        )

    return HttpResponse(

        '''

        <h1>
            ❌ Invalid Verification Link
        </h1>

        '''

    )

def send_verification_email(request):
    if request.method != "POST":
        return JsonResponse({
            "status": "failed",
            "message": "Invalid request"
        })

    print("🔥 VERIFY EMAIL API HIT")

    try:
        ####################################################
        # GET DATA
        ####################################################
        data = json.loads(request.body)
        email = data.get("email")

        ####################################################
        # CHECK EMPTY EMAIL
        ####################################################
        if not email:
            return JsonResponse({
                "status": "failed",
                "message": "Email is required"
            })

        ####################################################
        # CHECK EMAIL ALREADY REGISTERED
        ####################################################
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                "status": "failed",
                "message": "Email already registered"
            })

        ####################################################
        # GENERATE TOKEN
        ####################################################
        token = str(uuid.uuid4())

        ####################################################
        # SAVE SESSION
        ####################################################
        request.session['email_verification_token'] = token
        request.session['email_to_verify'] = email
        request.session.save()

        ####################################################
        # SEND EMAIL
        ####################################################
        verification_link = request.build_absolute_uri(
            reverse('verify_email', kwargs={'token': token})
        )

        print("🔥 TRYING TO SEND EMAIL")
        send_mail(
            subject='Verify Your Email - Seva Bandhu',
            message=f'''
Hi,

Please click the link below to verify your email address:

{verification_link}

If you did not request this email,
please ignore it.

Team Seva Bandhu
''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False
        )
        print("🔥 EMAIL SENT SUCCESSFULLY")

        return JsonResponse({
            "status": "success",
            "message": "Verification email sent"
        })

    except Exception as mail_error:
        print("🔥 EMAIL ERROR:", str(mail_error))
        return JsonResponse({
            "status": "failed",
            "message": str(mail_error)
        })


@csrf_exempt
def customer_phone_verify_complete(request):
    """Called by the client after successful Firebase phone confirmation.
    Marks the customer's phone as verified and optionally updates the contact number.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'failed', 'message': 'POST required'})

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': 'failed', 'message': 'Invalid JSON'})

    # Prefer session-stored user id for safety
    pending_user_id = request.session.get('pending_phone_user') or data.get('user_id')

    if not pending_user_id:
        return JsonResponse({'status': 'failed', 'message': 'No pending user in session'})

    try:
        user = User.objects.filter(id=pending_user_id).first()
        if not user:
            return JsonResponse({'status': 'failed', 'message': 'User not found'})

        cust = customer_signup.objects.filter(user=user).first()
        if not cust:
            return JsonResponse({'status': 'failed', 'message': 'Customer profile not found'})

        # Update phone if provided
        phone = data.get('phone')
        if phone:
            cust.contact = phone

        cust.phone_verified = True
        cust.save()

        # clear pending session
        try:
            request.session.pop('pending_phone_user')
        except Exception:
            pass

        return JsonResponse({'status': 'success'})

    except Exception as e:
        return JsonResponse({'status': 'failed', 'message': str(e)})
