from django.db import models
from  django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [
        ('guest', 'Guest'),
        ('host', 'Host'),
    ]

    
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    bio = models.TextField(blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='guest')

    def __str__(self):
        return f"{self.username}'s Profile"
