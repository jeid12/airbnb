import json
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from decimal import Decimal
from .models import Booking, Payment

# PayPal Settings for Development
PAYPAL_CLIENT_ID = "test"  # Replace with your PayPal Client ID
PAYPAL_CLIENT_SECRET = "test"  # Replace with your PayPal Client Secret
PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com"  # Sandbox URL

def get_paypal_access_token():
    """Get PayPal access token for API requests"""
    url = f"{PAYPAL_BASE_URL}/v1/oauth2/token"
    headers = {
        'Accept': 'application/json',
        'Accept-Language': 'en_US',
    }
    data = 'grant_type=client_credentials'
    
    response = requests.post(
        url, 
        headers=headers, 
        data=data, 
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
    )
    
    if response.status_code == 200:
        return response.json()['access_token']
    return None


@login_required
def payment_page(request, booking_id):
    """Display payment page with PayPal integration"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if booking is valid for payment
    if booking.status != 'pending':
        messages.error(request, "This booking cannot be paid for.")
        return redirect('bookings:booking_detail', booking_id=booking_id)
    
    # Create or get payment record
    payment, created = Payment.objects.get_or_create(
        booking=booking,
        defaults={
            'amount': booking.total_price,
            'currency': 'USD',
            'payment_method': 'paypal'
        }
    )
    
    context = {
        'booking': booking,
        'payment': payment,
        'paypal_client_id': PAYPAL_CLIENT_ID,
        'title': f'Payment for {booking.booking_reference}'
    }
    
    return render(request, 'bookings/payment.html', context)


@csrf_exempt
@require_POST
def create_paypal_order(request):
    """Create PayPal order for payment"""
    try:
        data = json.loads(request.body)
        booking_id = data.get('booking_id')
        
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        
        # Get PayPal access token
        access_token = get_paypal_access_token()
        if not access_token:
            return JsonResponse({'error': 'Failed to authenticate with PayPal'}, status=500)
        
        # Create PayPal order
        url = f"{PAYPAL_BASE_URL}/v2/checkout/orders"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        
        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": booking.booking_reference,
                "amount": {
                    "currency_code": "USD",
                    "value": str(booking.total_price)
                },
                "description": f"Booking for {booking.listing.title}",
                "custom_id": str(booking.id)
            }],
            "application_context": {
                "brand_name": "Kodesha Bookings",
                "landing_page": "BILLING",
                "user_action": "PAY_NOW",
                "return_url": request.build_absolute_uri(f'/bookings/payment/success/{booking.id}/'),
                "cancel_url": request.build_absolute_uri(f'/bookings/payment/cancel/{booking.id}/')
            }
        }
        
        response = requests.post(url, headers=headers, json=order_data)
        
        if response.status_code == 201:
            order = response.json()
            
            # Update payment record with PayPal order ID
            payment = Payment.objects.get(booking=booking)
            payment.paypal_order_id = order['id']
            payment.payment_id = order['id']
            payment.save()
            
            return JsonResponse({'id': order['id']})
        else:
            return JsonResponse({'error': 'Failed to create PayPal order'}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def capture_paypal_order(request, order_id):
    """Capture PayPal payment"""
    try:
        # Get PayPal access token
        access_token = get_paypal_access_token()
        if not access_token:
            return JsonResponse({'error': 'Failed to authenticate with PayPal'}, status=500)
        
        # Capture the order
        url = f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        
        response = requests.post(url, headers=headers)
        
        if response.status_code == 201:
            capture_data = response.json()
            
            # Find payment by PayPal order ID
            try:
                payment = Payment.objects.get(paypal_order_id=order_id)
                booking = payment.booking
                
                # Update payment status
                if capture_data['status'] == 'COMPLETED':
                    transaction = capture_data['purchase_units'][0]['payments']['captures'][0]
                    payment.mark_completed(
                        transaction_id=transaction['id'],
                        payer_email=capture_data.get('payer', {}).get('email_address')
                    )
                    
                    return JsonResponse({
                        'status': 'success',
                        'booking_id': booking.id,
                        'transaction_id': transaction['id']
                    })
                else:
                    payment.mark_failed()
                    return JsonResponse({'error': 'Payment was not completed'}, status=400)
                    
            except Payment.DoesNotExist:
                return JsonResponse({'error': 'Payment record not found'}, status=404)
        else:
            return JsonResponse({'error': 'Failed to capture payment'}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def payment_success(request, booking_id):
    """Handle successful payment"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    try:
        payment = Payment.objects.get(booking=booking)
        if payment.status == 'completed':
            messages.success(request, f'Payment successful! Your booking {booking.booking_reference} has been confirmed.')
        else:
            messages.warning(request, 'Payment is being processed. You will receive a confirmation email shortly.')
    except Payment.DoesNotExist:
        messages.error(request, 'Payment information not found.')
    
    return redirect('bookings:booking_detail', booking_id=booking_id)


@login_required
def payment_cancel(request, booking_id):
    """Handle cancelled payment"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    try:
        payment = Payment.objects.get(booking=booking)
        payment.status = 'cancelled'
        payment.save()
    except Payment.DoesNotExist:
        pass
    
    messages.info(request, 'Payment was cancelled. You can try again when ready.')
    return redirect('bookings:booking_detail', booking_id=booking_id)
