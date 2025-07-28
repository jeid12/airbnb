# app/urls.py (e.g., listings/urls.py)
from django.urls import path
from . import views

app_name = 'listings'  # This registers the namespace

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search_listings, name='search'),
    path('listings/', views.ListingView.as_view(), name='list'),
    path('listings/new/', views.ListingView.as_view(), name='create'),
    path('listings/<int:pk>/', views.ListingView.as_view(), name='detail'),
    path('listings/<int:pk>/edit/', views.ListingView.as_view(), name='edit'),
    path('listings/<int:pk>/delete/', views.ListingView.as_view(), name='delete'),
]
