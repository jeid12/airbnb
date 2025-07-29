from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from listing.models import Listing
from bookings.models import Booking
from .models import Review
from .forms import ReviewForm

@login_required
def create_review(request, booking_id):
    """Create a review for a completed booking"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if booking is completed
    if not booking.can_review:
        messages.error(request, "You can only review completed bookings.")
        return redirect('bookings:booking_detail', booking_id=booking_id)
    
    # Check if review already exists
    if hasattr(booking, 'review'):
        messages.info(request, "You have already reviewed this booking.")
        return redirect('bookings:booking_detail', booking_id=booking_id)
    
    if request.method == 'POST':
        form = ReviewForm(
            request.POST, 
            user=request.user, 
            listing=booking.listing,
            booking=booking
        )
        if form.is_valid():
            review = form.save()
            messages.success(request, "Thank you for your review!")
            return redirect('listing:detail', pk=booking.listing.id)
    else:
        form = ReviewForm(
            user=request.user, 
            listing=booking.listing,
            booking=booking
        )
    
    context = {
        'form': form,
        'booking': booking,
        'listing': booking.listing,
        'title': f'Review {booking.listing.title}'
    }
    return render(request, 'reviews/create_review.html', context)


def listing_reviews(request, listing_id):
    """Display all reviews for a listing"""
    listing = get_object_or_404(Listing, id=listing_id)
    reviews = listing.reviews.all()
    
    # Calculate average rating
    avg_rating = 0
    if reviews:
        total_rating = sum(review.rating for review in reviews)
        avg_rating = round(total_rating / len(reviews), 1)
    
    context = {
        'listing': listing,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'reviews_count': len(reviews),
        'title': f'Reviews for {listing.title}'
    }
    return render(request, 'reviews/listing_reviews.html', context)
