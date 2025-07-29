from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('create/<int:booking_id>/', views.create_review, name='create_review'),
    path('listing/<int:listing_id>/', views.listing_reviews, name='listing_reviews'),
]
