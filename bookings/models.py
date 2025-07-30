from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from listing.models import Listing

BOOKING_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('cancelled', 'Cancelled'),
    ('completed', 'Completed'),
]

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
    ('credit_card', 'Credit Card'),
    ('mtn_momo', 'MTN Mobile Money'),
    ('airtel_money', 'Airtel Money'),
]

class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='bookings')
    check_in = models.DateField()
    check_out = models.DateField()
    guests = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15, choices=BOOKING_STATUS_CHOICES, default='pending')
    booking_reference = models.CharField(max_length=20, unique=True, blank=True)
    special_requests = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {self.booking_reference} by {self.user.username} for {self.listing.title}"

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = self.generate_booking_reference()
        super().save(*args, **kwargs)

    def generate_booking_reference(self):
        import uuid
        return f"BK{str(uuid.uuid4().int)[:8].upper()}"

    def clean(self):
        """Validate booking data"""
        errors = {}
        
        if self.check_in and self.check_out:
            if self.check_in >= self.check_out:
                errors['check_out'] = ["Check-out date must be after check-in date"]
            
            if self.check_in < timezone.now().date():
                errors['check_in'] = ["Check-in date cannot be in the past"]
            
            # Check for overlapping bookings only if listing is available
            if hasattr(self, 'listing') and self.listing:
                overlapping_bookings = Booking.objects.filter(
                    listing=self.listing,
                    status__in=['confirmed', 'pending']
                ).exclude(id=self.id if self.id else None)
                
                for booking in overlapping_bookings:
                    if (self.check_in < booking.check_out and self.check_out > booking.check_in):
                        errors['__all__'] = ["These dates are not available"]
                        break
            elif self.listing_id:
                # Use listing_id if listing object not loaded
                overlapping_bookings = Booking.objects.filter(
                    listing_id=self.listing_id,
                    status__in=['confirmed', 'pending']
                ).exclude(id=self.id if self.id else None)
                
                for booking in overlapping_bookings:
                    if (self.check_in < booking.check_out and self.check_out > booking.check_in):
                        errors['__all__'] = ["These dates are not available"]
                        break

        if self.guests:
            # Check guest capacity if listing is available
            if hasattr(self, 'listing') and self.listing and self.guests > self.listing.guests:
                errors['guests'] = [f"Maximum {self.listing.guests} guests allowed"]
            elif self.listing_id and not hasattr(self, 'listing'):
                # Only check if we can safely get the listing
                try:
                    from listing.models import Listing
                    listing = Listing.objects.get(id=self.listing_id)
                    if self.guests > listing.guests:
                        errors['guests'] = [f"Maximum {listing.guests} guests allowed"]
                except Listing.DoesNotExist:
                    pass  # Will be caught by foreign key validation
        
        if errors:
            raise ValidationError(errors)

    @property
    def nights(self):
        """Calculate number of nights"""
        if self.check_in and self.check_out:
            return (self.check_out - self.check_in).days
        return 0

    @property
    def is_past(self):
        """Check if booking is in the past"""
        return self.check_out < timezone.now().date()

    @property
    def is_active(self):
        """Check if booking is currently active"""
        today = timezone.now().date()
        return self.check_in <= today <= self.check_out and self.status == 'confirmed'

    @property
    def can_cancel(self):
        """Check if booking can be cancelled"""
        return self.status in ['pending', 'confirmed'] and self.check_in > timezone.now().date()

    @property
    def can_review(self):
        """Check if user can leave a review"""
        return self.status == 'completed' and self.is_past

    def calculate_total_price(self):
        """Calculate total price based on nights and listing price"""
        return self.nights * self.listing.price_per_night

    def confirm_booking(self):
        """Confirm the booking"""
        self.status = 'confirmed'
        self.save()

    def cancel_booking(self):
        """Cancel the booking"""
        self.status = 'cancelled'
        self.save()

    def complete_booking(self):
        """Mark booking as completed"""
        if self.is_past and self.status == 'confirmed':
            self.status = 'completed'
            self.save()


class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='paypal')
    payment_id = models.CharField(max_length=100, unique=True, blank=True, null=True)  # PayPal order ID
    paypal_order_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    status = models.CharField(max_length=15, choices=PAYMENT_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # PayPal specific fields
    payer_email = models.EmailField(blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Mobile Money specific fields
    mobile_number = models.CharField(max_length=20, blank=True, null=True, help_text="Mobile number for mobile money payments")
    mobile_money_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    mobile_money_reference = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.payment_id or 'PENDING'} for {self.booking.booking_reference}"
    
    def mark_completed(self, transaction_id=None, payer_email=None, mobile_money_ref=None):
        """Mark payment as completed and update booking status"""
        self.status = 'completed'
        if transaction_id:
            if self.payment_method in ['mtn_momo', 'airtel_money']:
                self.mobile_money_transaction_id = transaction_id
            else:
                self.transaction_id = transaction_id
        if payer_email:
            self.payer_email = payer_email
        if mobile_money_ref:
            self.mobile_money_reference = mobile_money_ref
        self.save()
        
        # Update booking status to confirmed
        self.booking.confirm_booking()
    
    def mark_failed(self):
        """Mark payment as failed"""
        self.status = 'failed'
        self.save()
    
    @property
    def is_mobile_money(self):
        """Check if payment method is mobile money"""
        return self.payment_method in ['mtn_momo', 'airtel_money']
    
    def get_amount_in_rwf(self):
        """Convert amount to RWF for mobile money payments"""
        if self.currency == 'RWF':
            return self.amount
        # Simple conversion rate - in production, use real-time rates
        usd_to_rwf_rate = 1300  # Approximate rate
        return self.amount * usd_to_rwf_rate if self.currency == 'USD' else self.amount
