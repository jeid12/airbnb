from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from listing.models import Listing

class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reviews')
    booking = models.OneToOneField('bookings.Booking', on_delete=models.CASCADE, null=True, blank=True, related_name='review')
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    comment = models.TextField(help_text="Your review comment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'listing']  # One review per user per listing
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username} on {self.listing.title} ({self.rating}★)"
    
    @property
    def star_display(self):
        """Return stars as string for display"""
        return '★' * self.rating + '☆' * (5 - self.rating)
