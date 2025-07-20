from django.db import models
from django.contrib.auth.models import User

PROPERTY_TYPE_CHOICES = [
    ('entire_place', 'Entire Place'),
    ('private_room', 'Private Room'),
    ('shared_room', 'Shared Room'),
]

class Listing(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    guests = models.PositiveIntegerField()
    bedrooms = models.PositiveIntegerField()
    beds = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    image = models.ImageField(upload_to='listings/', null=True, blank=True)
    host = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
