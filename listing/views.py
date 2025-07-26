from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from .forms import ListingForm
from .models import Listing

def home(request):
    listings = Listing.objects.all()[:6]  
    return render(request, 'index.html', {'listings': listings})



class ListingView(View):
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
            return render(request, 'listings/detail.html', {'listing': listing})

        listings = Listing.objects.filter(is_active=True)
        return render(request, 'listings/list.html', {'listings': listings})

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
    @method_decorator(login_required)
    def delete(self, request, pk):
        listing = get_object_or_404(Listing, pk=pk)
        listing.delete()
        return redirect('listings:list')
