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
from .mobile_money_service import MobileMoneyManager, MobileMoneyError

# PayPal Settings for Development
PAYPAL_CLIENT_ID = getattr(settings, 'PAYPAL_CLIENT_ID', 'test')
PAYPAL_CLIENT_SECRET = getattr(settings, 'PAYPAL_CLIENT_SECRET', 'test')
PAYPAL_BASE_URL = getattr(settings, 'PAYPAL_SANDBOX_URL', 'https://sandbox.paypal.com')

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
    """Display payment page with PayPal and Mobile Money integration"""
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
    
    # Calculate amount in RWF for mobile money
    mobile_money_manager = MobileMoneyManager()
    amount_rwf = int(booking.total_price * 1300)  # Simple conversion - use real rates in production
    
    context = {
        'booking': booking,
        'payment': payment,
        'paypal_client_id': PAYPAL_CLIENT_ID,
        'amount_usd': booking.total_price,
        'amount_rwf': amount_rwf,
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


@csrf_exempt
@require_POST
def initiate_mobile_money_payment(request):
    """Initiate mobile money payment"""
    try:
        data = json.loads(request.body)
        booking_id = data.get('booking_id')
        payment_method = data.get('payment_method')  # 'mtn_momo' or 'airtel_money'
        mobile_number = data.get('mobile_number')
        
        # Validate required fields
        if not all([booking_id, payment_method, mobile_number]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        if payment_method not in ['mtn_momo', 'airtel_money']:
            return JsonResponse({'error': 'Invalid payment method'}, status=400)
        
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        
        # Get or update payment record
        payment, created = Payment.objects.get_or_create(
            booking=booking,
            defaults={
                'amount': booking.total_price,
                'currency': 'RWF',
                'payment_method': payment_method
            }
        )
        
        # Update payment method and mobile number
        payment.payment_method = payment_method
        payment.mobile_number = mobile_number
        payment.currency = 'RWF'
        payment.amount = payment.get_amount_in_rwf()  # Convert to RWF
        
        # Initialize mobile money manager
        mobile_money_manager = MobileMoneyManager()
        
        try:
            # Validate mobile number
            validated_number = mobile_money_manager.validate_mobile_number(mobile_number, payment_method)
            payment.mobile_number = validated_number
            
            # Request payment
            result = mobile_money_manager.request_payment(
                payment_method=payment_method,
                amount=payment.amount,
                mobile_number=validated_number,
                external_reference=booking.booking_reference,
                description=f"Payment for {booking.listing.title}"
            )
            
            # Update payment record with reference
            payment.mobile_money_reference = result['reference_id']
            payment.payment_id = result['reference_id']
            payment.save()
            
            return JsonResponse({
                'status': 'success',
                'message': result['message'],
                'reference_id': result['reference_id'],
                'payment_id': payment.id
            })
            
        except MobileMoneyError as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def check_mobile_money_status(request):
    """Check mobile money payment status"""
    try:
        data = json.loads(request.body)
        payment_id = data.get('payment_id')
        
        if not payment_id:
            return JsonResponse({'error': 'Payment ID required'}, status=400)
        
        payment = get_object_or_404(Payment, id=payment_id, booking__user=request.user)
        
        if not payment.is_mobile_money:
            return JsonResponse({'error': 'Not a mobile money payment'}, status=400)
        
        mobile_money_manager = MobileMoneyManager()
        
        try:
            status_result = mobile_money_manager.check_payment_status(
                payment_method=payment.payment_method,
                reference_id=payment.mobile_money_reference
            )
            
            # Update payment based on status
            if status_result['status'] == 'SUCCESSFUL':
                payment.mark_completed(
                    transaction_id=status_result.get('transaction_id'),
                    mobile_money_ref=status_result.get('reference_id')
                )
                return JsonResponse({
                    'status': 'completed',
                    'message': 'Payment completed successfully!',
                    'transaction_id': status_result.get('transaction_id')
                })
            elif status_result['status'] == 'FAILED':
                payment.mark_failed()
                return JsonResponse({
                    'status': 'failed',
                    'message': 'Payment failed. Please try again.',
                    'reason': status_result.get('reason', 'Unknown error')
                })
            else:  # PENDING
                return JsonResponse({
                    'status': 'pending',
                    'message': 'Payment is still being processed. Please wait...'
                })
                
        except MobileMoneyError as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def mobile_money_success(request, payment_id):
    """Handle successful mobile money payment"""
    payment = get_object_or_404(Payment, id=payment_id, booking__user=request.user)
    booking = payment.booking
    
    if payment.status == 'completed':
        messages.success(request, f'Payment completed successfully! Your booking {booking.booking_reference} has been confirmed.')
    else:
        messages.info(request, 'Payment is being processed. You will receive a confirmation shortly.')
    
    return redirect('bookings:booking_detail', booking_id=booking.id)
