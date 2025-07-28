from django.http import HttpResponseForbidden
from functools import wraps
from django.shortcuts import render, get_object_or_404
from .models import Listing

def host_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            
            return  HttpResponseForbidden(render(request, '403_forbidden.html'))
        if getattr(user, 'role', None) != 'host':
            return HttpResponseForbidden(render(request, '403_forbidden.html'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def property_access_required(view_func):
    """
    Decorator that restricts hosts to only view their own properties.
    Guests and unauthenticated users can view any property.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        
        # Get the listing pk from URL parameters
        listing_pk = kwargs.get('pk')
        if listing_pk:
            listing = get_object_or_404(Listing, pk=listing_pk)
            
            # Check if user is a host and trying to view someone else's property
            if (user.is_authenticated and 
                hasattr(user, 'role') and 
                user.role == 'host' and 
                listing.host != user):
                return HttpResponseForbidden(render(request, '403_forbidden.html'))
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view
