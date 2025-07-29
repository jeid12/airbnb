from django.contrib import admin
from .models import Booking, Payment

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_reference', 'user', 'listing', 'check_in', 'check_out', 'status', 'total_price', 'created_at']
    list_filter = ['status', 'created_at', 'check_in', 'check_out']
    search_fields = ['booking_reference', 'user__username', 'listing__title', 'user__email']
    readonly_fields = ['booking_reference', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('booking_reference', 'user', 'listing', 'status')
        }),
        ('Stay Details', {
            'fields': ('check_in', 'check_out', 'guests', 'special_requests')
        }),
        ('Pricing', {
            'fields': ('total_price',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # Only allow deletion of pending/cancelled bookings
        if obj and obj.status in ['confirmed', 'completed']:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'booking', 'amount', 'currency', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'currency', 'created_at']
    search_fields = ['payment_id', 'booking__booking_reference', 'transaction_id', 'payer_email']
    readonly_fields = ['payment_id', 'paypal_order_id', 'transaction_id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('booking', 'payment_method', 'amount', 'currency', 'status')
        }),
        ('PayPal Details', {
            'fields': ('payment_id', 'paypal_order_id', 'transaction_id', 'payer_email'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Payments should be created through the payment process
        return False
