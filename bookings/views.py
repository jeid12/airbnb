from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from .models import Booking
from .forms import BookingForm, BookingCancelForm
from listing.models import Listing
from decimal import Decimal
import json


@login_required
def create_booking(request, listing_id):
    """Create a new booking for a listing"""
    listing = get_object_or_404(Listing, id=listing_id, is_active=True)
    
    # Prevent hosts from booking their own properties
    if request.user == listing.host:
        messages.error(request, "You cannot book your own property.")
        return redirect('listing:detail', pk=listing_id)
    
    # Only guests can make bookings
    if request.user.role != 'guest':
        messages.error(request, "Only guests can make bookings.")
        return redirect('listing:detail', pk=listing_id)
    
    if request.method == 'POST':
        form = BookingForm(request.POST, listing=listing)
        if form.is_valid():
            try:
                booking = form.save(commit=False)
                booking.user = request.user
                booking.listing = listing
                booking.total_price = booking.calculate_total_price()
                
                # Run model validation after all fields are set
                booking.full_clean()
                booking.save()
                
                messages.success(request, f'Booking created successfully! Reference: {booking.booking_reference}')
                return redirect('bookings:payment_page', booking_id=booking.id)
                
            except ValidationError as e:
                if hasattr(e, 'message_dict'):
                    for field, errors in e.message_dict.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
                else:
                    for error in e.messages:
                        messages.error(request, error)
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        form = BookingForm(listing=listing)
    
    context = {
        'form': form,
        'listing': listing,
        'title': f'Book {listing.title}'
    }
    return render(request, 'bookings/create_booking.html', context)


@login_required
def booking_detail(request, booking_id):
    """View booking details"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permissions
    if request.user != booking.user and request.user != booking.listing.host and request.user.role != 'admin':
        return HttpResponseForbidden("You don't have permission to view this booking.")
    
    context = {
        'booking': booking,
        'title': f'Booking {booking.booking_reference}'
    }
    return render(request, 'bookings/booking_detail.html', context)


@login_required
def my_bookings(request):
    """List user's bookings (for guests)"""
    if request.user.role not in ['guest', 'admin']:
        messages.error(request, "Access denied.")
        return redirect('listing:home')
    
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    bookings = Booking.objects.filter(user=request.user)
    
    if status_filter != 'all':
        bookings = bookings.filter(status=status_filter)
    
    if search_query:
        bookings = bookings.filter(
            Q(listing__title__icontains=search_query) |
            Q(booking_reference__icontains=search_query) |
            Q(listing__location__icontains=search_query)
        )
    
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'title': 'My Bookings'
    }
    return render(request, 'bookings/my_bookings.html', context)


@login_required
def host_bookings(request):
    """List bookings for host's properties"""
    if request.user.role not in ['host', 'admin']:
        messages.error(request, "Access denied.")
        return redirect('listing:home')
    
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    bookings = Booking.objects.filter(listing__host=request.user)
    
    if status_filter != 'all':
        bookings = bookings.filter(status=status_filter)
    
    if search_query:
        bookings = bookings.filter(
            Q(user__username__icontains=search_query) |
            Q(booking_reference__icontains=search_query) |
            Q(listing__title__icontains=search_query)
        )
    
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'title': 'Received Bookings'
    }
    return render(request, 'bookings/host_bookings.html', context)


@login_required
@require_POST
def cancel_booking(request, booking_id):
    """Cancel a booking"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permissions
    if request.user != booking.user and request.user.role != 'admin':
        return HttpResponseForbidden("You don't have permission to cancel this booking.")
    
    if not booking.can_cancel:
        messages.error(request, "This booking cannot be cancelled.")
        return redirect('bookings:booking_detail', booking_id=booking_id)
    
    form = BookingCancelForm(request.POST)
    if form.is_valid():
        booking.cancel_booking()
        messages.success(request, f'Booking {booking.booking_reference} has been cancelled.')
        return redirect('bookings:my_bookings')
    else:
        messages.error(request, "Please confirm the cancellation.")
        return redirect('bookings:booking_detail', booking_id=booking_id)


@login_required
def confirm_booking(request, booking_id):
    """Confirm a booking (for hosts or after payment)"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permissions - only hosts can confirm or admin
    if request.user != booking.listing.host and request.user.role != 'admin':
        return HttpResponseForbidden("You don't have permission to confirm this booking.")
    
    if booking.status == 'pending':
        booking.confirm_booking()
        messages.success(request, f'Booking {booking.booking_reference} has been confirmed.')
    else:
        messages.info(request, 'Booking is already confirmed or cannot be confirmed.')
    
    return redirect('bookings:booking_detail', booking_id=booking_id)


def check_availability(request):
    """AJAX endpoint to check availability"""
    if request.method == 'GET':
        listing_id = request.GET.get('listing_id')
        check_in = request.GET.get('check_in')
        check_out = request.GET.get('check_out')
        
        if not all([listing_id, check_in, check_out]):
            return JsonResponse({'available': False, 'message': 'Missing parameters'})
        
        try:
            listing = Listing.objects.get(id=listing_id)
            from datetime import datetime
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            
            # Check for overlapping bookings
            overlapping = Booking.objects.filter(
                listing=listing,
                status__in=['confirmed', 'pending'],
                check_in__lt=check_out_date,
                check_out__gt=check_in_date
            ).exists()
            
            nights = (check_out_date - check_in_date).days
            total_price = nights * listing.price_per_night
            
            return JsonResponse({
                'available': not overlapping,
                'nights': nights,
                'price_per_night': float(listing.price_per_night),
                'total_price': float(total_price),
                'message': 'Available' if not overlapping else 'Not available for these dates'
            })
            
        except Exception as e:
            return JsonResponse({'available': False, 'message': str(e)})
    
    return JsonResponse({'available': False, 'message': 'Invalid request method'})


@login_required
def booking_confirmation(request, booking_id):
    """Show booking confirmation page before payment"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Only the booking user can see confirmation
    if request.user != booking.user:
        return HttpResponseForbidden("You don't have permission to view this booking.")
    
    context = {
        'booking': booking,
        'title': f'Confirm Booking {booking.booking_reference}'
    }
    return render(request, 'bookings/booking_confirmation.html', context)
