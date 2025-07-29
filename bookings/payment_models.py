from django.db import models
from django.conf import settings
from .models import Booking

PAYMENT_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
    ('refunded', 'Refunded'),
]

PAYMENT_METHOD_CHOICES = [
    ('paypal', 'PayPal'),
    ('stripe', 'Stripe'),
    ('card', 'Credit Card'),
]

class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    payment_id = models.CharField(max_length=100, unique=True)  # PayPal transaction ID
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='paypal')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=15, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # PayPal specific fields
    paypal_order_id = models.CharField(max_length=100, blank=True, null=True)
    paypal_payer_id = models.CharField(max_length=100, blank=True, null=True)
    paypal_payer_email = models.EmailField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.payment_id} for {self.booking.booking_reference}"

    @property
    def is_successful(self):
        return self.status == 'completed'

    def mark_as_completed(self):
        """Mark payment as completed and confirm booking"""
        from django.utils import timezone
        self.status = 'completed'
        self.paid_at = timezone.now()
        self.save()
        
        # Confirm the booking
        self.booking.confirm_booking()

    def mark_as_failed(self):
        """Mark payment as failed"""
        self.status = 'failed'
        self.save()
