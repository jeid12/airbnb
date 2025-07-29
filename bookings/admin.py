from django.contrib import admin
from .models import Booking

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
