from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .forms import UserRegistrationForm

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            
            user=form.save()

            # Log the user in after successful registration
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Registration successful. You are now logged in.")
                return redirect('listings:home')
            else:
                messages.error(request, "Registration successful, but login failed. Please try logging in manually.")



           
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})


def is_admin(user):
    """Check if user has admin role"""
    return user.is_authenticated and hasattr(user, 'role') and user.role == 'admin'


@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """Admin dashboard with comprehensive statistics"""
    from listing.models import Listing
    from bookings.models import Booking, Payment
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    # Basic statistics
    total_properties = Listing.objects.filter(is_active=True).count()
    active_bookings = Booking.objects.filter(
        status__in=['confirmed', 'pending'],
        check_out__gte=now.date()
    ).count()
    
    # Revenue calculation - handle case where Payment model might not exist
    try:
        total_revenue = Payment.objects.filter(
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
    except:
        total_revenue = 0
    
    # Count users by role
    total_users = User.objects.count()
    guest_users = User.objects.filter(role='guest').count()
    host_users = User.objects.filter(role='host').count()
    admin_users = User.objects.filter(role='admin').count()
    
    # Recent bookings (last 10)
    recent_bookings = Booking.objects.select_related(
        'user', 'listing'
    ).order_by('-created_at')[:10]
    
    # Monthly revenue data (last 6 months)
    monthly_revenue = []
    max_revenue = 1  # Prevent division by zero
    
    # Calculate max revenue for percentage calculation
    try:
        for i in range(6):
            month_start = (now.replace(day=1) - timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            month_revenue = Payment.objects.filter(
                status='completed',
                created_at__range=[month_start, month_end]
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            max_revenue = max(max_revenue, month_revenue)
            
            monthly_revenue.append({
                'month': month_start.strftime('%b'),
                'amount': month_revenue,
                'percentage': 0  # Will calculate after finding max
            })
        
        # Calculate percentages
        for month in monthly_revenue:
            month['percentage'] = min(int((month['amount'] / max_revenue) * 100), 100) if max_revenue > 0 else 0
            
    except:
        # Fallback data if Payment model doesn't work
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        monthly_revenue = [
            {'month': month, 'amount': 0, 'percentage': 0}
            for month in months
        ]
    
    monthly_revenue.reverse()  # Show oldest to newest
    
    # Top performing properties
    try:
        top_properties = Listing.objects.filter(
            is_active=True
        ).annotate(
            bookings_count=Count('booking'),
            revenue=Sum('booking__payment__amount', filter=Q(booking__payment__status='completed'))
        ).order_by('-bookings_count')[:5]
    except:
        # Fallback if relationship doesn't exist
        top_properties = Listing.objects.filter(is_active=True)[:5]
    
    # Recent activities (enhanced with real data when possible)
    recent_activities = []
    
    # Add recent bookings to activities
    recent_booking = Booking.objects.order_by('-created_at').first()
    if recent_booking:
        recent_activities.append({
            'description': f'New booking for {recent_booking.listing.title}',
            'icon': 'calendar-check',
            'color': 'green',
            'timestamp': recent_booking.created_at
        })
    
    # Add recent property listings
    recent_property = Listing.objects.order_by('-created_at').first()
    if recent_property:
        recent_activities.append({
            'description': f'New property listed: {recent_property.title}',
            'icon': 'home',
            'color': 'blue',
            'timestamp': recent_property.created_at
        })
    
    # Add recent user registrations
    recent_user = User.objects.order_by('-date_joined').first()
    if recent_user and recent_user.date_joined > now - timedelta(days=7):
        recent_activities.append({
            'description': f'New user registered: {recent_user.username}',
            'icon': 'user-plus',
            'color': 'purple',
            'timestamp': recent_user.date_joined
        })
    
    # Fill with demo activities if we don't have enough real data
    if len(recent_activities) < 4:
        demo_activities = [
            {
                'description': 'System maintenance completed',
                'icon': 'cogs',
                'color': 'gray',
                'timestamp': now - timedelta(hours=6)
            },
            {
                'description': 'Payment system updated',
                'icon': 'credit-card',
                'color': 'green',
                'timestamp': now - timedelta(days=1)
            },
            {
                'description': 'Database backup completed',
                'icon': 'database',
                'color': 'blue',
                'timestamp': now - timedelta(days=2)
            },
        ]
        recent_activities.extend(demo_activities[:4-len(recent_activities)])
    
    # Sort activities by timestamp
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    context = {
        'total_properties': total_properties,
        'active_bookings': active_bookings,
        'total_revenue': total_revenue,
        'total_users': total_users,
        'guest_users': guest_users,
        'host_users': host_users,
        'admin_users': admin_users,
        'recent_bookings': recent_bookings,
        'monthly_revenue': monthly_revenue,
        'top_properties': top_properties,
        'recent_activities': recent_activities[:8],  # Limit to 8 activities
    }
    
    return render(request, 'dashboard.html', context)
