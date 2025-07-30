from django.urls import path
from . import views
from . import payment_views

app_name = 'bookings'

urlpatterns = [
    # Booking creation and details
    path('create/<int:listing_id>/', views.create_booking, name='create_booking'),
    path('<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('<int:booking_id>/confirm/', views.booking_confirmation, name='booking_confirmation'),
    
    # Payment URLs
    path('payment/<int:booking_id>/', payment_views.payment_page, name='payment_page'),
    path('payment/create-order/', payment_views.create_paypal_order, name='create_paypal_order'),
    path('payment/capture-order/<str:order_id>/', payment_views.capture_paypal_order, name='capture_paypal_order'),
    path('payment/success/<int:booking_id>/', payment_views.payment_success, name='payment_success'),
    path('payment/cancel/<int:booking_id>/', payment_views.payment_cancel, name='payment_cancel'),
    
    # Mobile Money URLs
    path('payment/mobile-money/initiate/', payment_views.initiate_mobile_money_payment, name='initiate_mobile_money'),
    path('payment/mobile-money/status/', payment_views.check_mobile_money_status, name='check_mobile_money_status'),
    path('payment/mobile-money/success/<int:payment_id>/', payment_views.mobile_money_success, name='mobile_money_success'),
    
    # Booking management
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('host-bookings/', views.host_bookings, name='host_bookings'),
    
    # Booking actions
    path('<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('<int:booking_id>/confirm/', views.confirm_booking, name='confirm_booking'),
    
    # AJAX endpoints
    path('check-availability/', views.check_availability, name='check_availability'),
]
