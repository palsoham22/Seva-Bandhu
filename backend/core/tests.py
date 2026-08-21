import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import SignupEmailOTP, customer_signup


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='noreply@example.com',
)
class CustomerSignupOTPTests(TestCase):
    def send_code(self, username='newcustomer', email='new@example.com'):
        response = self.client.post(
            reverse('send_signup_otp'),
            data={'username': username, 'email': email},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        code = re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)
        return code

    def test_complete_signup_requires_and_uses_verified_otp(self):
        self.assertContains(self.client.get(reverse('customer_signup')), 'Verify email')
        code = self.send_code()
        wrong = self.client.post(reverse('verify_signup_otp'), data={'code': '000000'}, content_type='application/json')
        self.assertEqual(wrong.status_code, 400)
        verified = self.client.post(reverse('verify_signup_otp'), data={'code': code}, content_type='application/json')
        self.assertEqual(verified.json()['status'], 'verified')
        response = self.client.post(reverse('customer_signup'), {
            'username': 'newcustomer', 'email': 'new@example.com', 'contact': '9000000001', 'password': 'Secure-pass-123',
        })
        self.assertRedirects(response, reverse('customer_login'))
        customer = customer_signup.objects.get(username='newcustomer')
        self.assertTrue(customer.email_verified)
        self.assertTrue(customer.user.check_password('Secure-pass-123'))
        self.assertNotEqual(customer.password, 'Secure-pass-123')

    def test_expired_and_resend_codes(self):
        self.send_code()
        verification = SignupEmailOTP.objects.get(email='new@example.com')
        verification.expires_at = timezone.now() - timedelta(seconds=1)
        verification.save()
        expired = self.client.post(reverse('verify_signup_otp'), data={'code': '123456'}, content_type='application/json')
        self.assertEqual(expired.json()['status'], 'expired')
        cooldown = self.client.post(reverse('send_signup_otp'), data={'username': 'newcustomer', 'email': 'new@example.com'}, content_type='application/json')
        self.assertEqual(cooldown.status_code, 429)
        verification.resend_available_at = timezone.now() - timedelta(seconds=1)
        verification.save()
        resent = self.client.post(reverse('send_signup_otp'), data={'username': 'newcustomer', 'email': 'new@example.com'}, content_type='application/json')
        self.assertEqual(resent.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)

    def test_signup_identity_survives_refresh_after_requesting_code(self):
        self.send_code(username='refresh-user', email='refresh@example.com')
        response = self.client.get(reverse('customer_signup'))
        self.assertContains(response, 'value="refresh-user"')
        self.assertContains(response, 'value="refresh@example.com"')

    def test_existing_email_and_username_are_rejected(self):
        User.objects.create_user(username='taken', email='taken@example.com', password='pass')
        email_response = self.client.post(reverse('send_signup_otp'), data={'username': 'available', 'email': 'taken@example.com'}, content_type='application/json')
        self.assertEqual(email_response.status_code, 409)
        self.assertEqual(email_response.json()['message'], 'An account with this email already exists.')
        username_response = self.client.post(reverse('send_signup_otp'), data={'username': 'taken', 'email': 'available@example.com'}, content_type='application/json')
        self.assertEqual(username_response.status_code, 409)
        self.assertEqual(username_response.json()['message'], 'This username is already taken.')


class CustomerLoginTests(TestCase):
    def make_customer(self, username, verified=True):
        user = User.objects.create_user(username=username, email=f'{username}@example.com', password='correct-password')
        customer_signup.objects.create(user=user, username=username, email=user.email, contact=f'90000000{user.id}', password=user.password, email_verified=verified)

    def test_login_success_wrong_password_unknown_and_unverified(self):
        self.make_customer('verified', verified=True)
        self.make_customer('unverified', verified=False)
        success = self.client.post(reverse('customer_login'), {'username': 'VERIFIED', 'password': 'correct-password'})
        self.assertRedirects(success, reverse('service_selection'))
        self.client.logout()
        wrong = self.client.post(reverse('customer_login'), {'username': 'verified', 'password': 'wrong-password'})
        self.assertContains(wrong, 'Incorrect password')
        unknown = self.client.post(reverse('customer_login'), {'username': 'unknown', 'password': 'anything'})
        self.assertContains(unknown, 'No account was found')
        unverified = self.client.post(reverse('customer_login'), {'username': 'unverified', 'password': 'correct-password'})
        self.assertContains(unverified, 'has not verified its email')
