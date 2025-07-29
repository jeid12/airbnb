from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from .decolarator import host_required, property_access_required
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Q
from django.utils import timezone

from .forms import ListingForm
from .models import Listing

def home(request):
    listings = Listing.objects.filter(is_active=True)
    
    # Search functionality
    query = request.GET.get('q', '').strip()
    property_type = request.GET.get('property_type', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    guests = request.GET.get('guests', '')
    
    # Filter by search query (location, title, description)
    if query:
        listings = listings.filter(
            Q(location__icontains=query) |
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Filter by property type
    if property_type:
        listings = listings.filter(property_type=property_type)
    
    # Filter by price range
    if min_price:
        try:
            listings = listings.filter(price_per_night__gte=float(min_price))
        except ValueError:
            pass
    
    if max_price:
        try:
            listings = listings.filter(price_per_night__lte=float(max_price))
        except ValueError:
            pass
    
    # Filter by guest capacity
    if guests:
        try:
            listings = listings.filter(guests__gte=int(guests))
        except ValueError:
            pass
    
    # If no search parameters are provided, show only featured listings (first 6)
    if not any([query, property_type, min_price, max_price, guests]):
        listings = listings[:6]
    
    # Get property type choices for the filter dropdown
    from .models import PROPERTY_TYPE_CHOICES
    
    context = {
        'listings': listings,
        'property_type_choices': PROPERTY_TYPE_CHOICES,
        'search_query': query,
        'selected_property_type': property_type,
        'min_price': min_price,
        'max_price': max_price,
        'guests': guests,
        'is_search': any([query, property_type, min_price, max_price, guests])
    }
    
    return render(request, 'index.html', context)

def search_listings(request):
    """Dedicated search page with advanced filtering"""
    listings = Listing.objects.filter(is_active=True)
    
    # Search functionality
    query = request.GET.get('q', '').strip()
    property_type = request.GET.get('property_type', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    guests = request.GET.get('guests', '')
    sort_by = request.GET.get('sort', 'newest')
    
    # Filter by search query (location, title, description)
    if query:
        listings = listings.filter(
            Q(location__icontains=query) |
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Filter by property type
    if property_type:
        listings = listings.filter(property_type=property_type)
    
    # Filter by price range
    if min_price:
        try:
            listings = listings.filter(price_per_night__gte=float(min_price))
        except ValueError:
            pass
    
    if max_price:
        try:
            listings = listings.filter(price_per_night__lte=float(max_price))
        except ValueError:
            pass
    
    # Filter by guest capacity
    if guests:
        try:
            listings = listings.filter(guests__gte=int(guests))
        except ValueError:
            pass
    
    # Apply sorting
    if sort_by == 'price_low':
        listings = listings.order_by('price_per_night')
    elif sort_by == 'price_high':
        listings = listings.order_by('-price_per_night')
    elif sort_by == 'guests':
        listings = listings.order_by('-guests')
    else:  # newest or default
        listings = listings.order_by('-created_at')
    
    # Get property type choices for the filter dropdown
    from .models import PROPERTY_TYPE_CHOICES
    
    context = {
        'listings': listings,
        'property_type_choices': PROPERTY_TYPE_CHOICES,
        'search_query': query,
        'selected_property_type': property_type,
        'min_price': min_price,
        'max_price': max_price,
        'guests': guests,
        'sort_by': sort_by,
    }
    
    return render(request, 'listings/search_results.html', context)



class ListingView(View):
    @method_decorator(property_access_required)
    def get(self, request, pk=None):
        if pk is None and request.path.endswith('/new/'):
            form = ListingForm()
            return render(request, 'listings/form.html', {'form': form, 'action': 'Create'})
        
        if pk is not None and request.path.endswith('/edit/'):
            listing = get_object_or_404(Listing, pk=pk)
            form = ListingForm(instance=listing)
            return render(request, 'listings/form.html', {'form': form, 'action': 'Edit', 'listing': listing})

        if pk is not None:
            listing = get_object_or_404(Listing, pk=pk)
            
            # Get related listings for guests
            related_listings = []
            if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'guest':
                # Calculate price range (±30% of current listing price)
                price_min = float(listing.price_per_night) * 0.7
                price_max = float(listing.price_per_night) * 1.3
                
                # Get related listings based on location and price range
                related_listings = Listing.objects.filter(
                    is_active=True,
                    location__icontains=listing.location.split(',')[0],  # Match by city/area
                    price_per_night__gte=price_min,
                    price_per_night__lte=price_max
                ).exclude(pk=listing.pk).order_by('?')[:4]  # Random order, limit to 4
                
                # If we don't have enough related listings, get more based on just location
                if len(related_listings) < 4:
                    additional_listings = Listing.objects.filter(
                        is_active=True,
                        location__icontains=listing.location.split(',')[0]
                    ).exclude(
                        pk__in=[listing.pk] + list(related_listings.values_list('pk', flat=True))
                    ).order_by('?')[:4-len(related_listings)]
                    
                    related_listings = list(related_listings) + list(additional_listings)
            
            context = {
                'listing': listing,
                'related_listings': related_listings,
                'today_date': timezone.now().date()
            }
            return render(request, 'listings/detail.html', context)

        listings = Listing.objects.filter(is_active=True)
        return render(request, 'listings/list.html', {'listings': listings})

    @method_decorator(host_required)
    @method_decorator(login_required)
    def post(self, request, pk=None):
        if pk is None and request.path.endswith('/new/'):
            form = ListingForm(request.POST, request.FILES)
            if form.is_valid():
                listing = form.save(commit=False)
                listing.host = request.user
                listing.save()
                return redirect('listings:list')
            return render(request, 'listings/form.html', {'form': form, 'action': 'Create'})

        if pk is not None and request.path.endswith('/edit/'):
            listing = get_object_or_404(Listing, pk=pk)
            form = ListingForm(request.POST, request.FILES, instance=listing)
            if form.is_valid():
                form.save()
                return redirect('listings:detail', pk=pk)
            return render(request, 'listings/form.html', {'form': form, 'action': 'Edit', 'listing': listing})

        return redirect('listings:list')
    @method_decorator(host_required)
    @method_decorator(login_required)
    def delete(self, request, pk):
        listing = get_object_or_404(Listing, pk=pk)
        listing.delete()
        return redirect('listings:list')
