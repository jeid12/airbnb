"""
Mobile Money Payment Services for Rwanda
Integrates with MTN Mobile Money and Airtel Money APIs
"""
import requests
import json
import uuid
import hashlib
import time
from decimal import Decimal
from django.conf import settings
from django.utils import timezone


class MobileMoneyError(Exception):
    """Custom exception for mobile money errors"""
    pass


class MTNMoMoService:
    """MTN Mobile Money API Integration"""
    
    def __init__(self):
        # In production, these should be in settings
        self.api_user = getattr(settings, 'MTN_API_USER', 'sandbox')
        self.api_key = getattr(settings, 'MTN_API_KEY', 'sandbox_key')
        self.subscription_key = getattr(settings, 'MTN_SUBSCRIPTION_KEY', 'test_key')
        self.base_url = getattr(settings, 'MTN_BASE_URL', 'https://sandbox.momodeveloper.mtn.com')
        self.environment = getattr(settings, 'MTN_ENVIRONMENT', 'sandbox')
    
    def generate_uuid(self):
        """Generate UUID for transaction reference"""
        return str(uuid.uuid4())
    
    def get_auth_token(self):
        """Get authorization token from MTN API"""
        url = f"{self.base_url}/collection/token/"
        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-Type': 'application/json'
        }
        
        # For sandbox, we simulate token generation
        if self.environment == 'sandbox':
            return 'sandbox_token_' + str(int(time.time()))
        
        try:
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                return response.json().get('access_token')
            else:
                raise MobileMoneyError(f"Failed to get MTN auth token: {response.text}")
        except requests.RequestException as e:
            raise MobileMoneyError(f"MTN API connection error: {str(e)}")
    
    def request_payment(self, amount, mobile_number, external_reference, payer_message="Payment for booking"):
        """Request payment from customer's mobile wallet"""
        reference_id = self.generate_uuid()
        
        # For sandbox, simulate successful payment request
        if self.environment == 'sandbox':
            return {
                'reference_id': reference_id,
                'status': 'PENDING',
                'message': 'Payment request sent successfully (Sandbox)'
            }
        
        url = f"{self.base_url}/collection/v1_0/requesttopay"
        token = self.get_auth_token()
        
        headers = {
            'Authorization': f'Bearer {token}',
            'X-Reference-Id': reference_id,
            'X-Target-Environment': self.environment,
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'amount': str(amount),
            'currency': 'RWF',
            'externalId': external_reference,
            'payer': {
                'partyIdType': 'MSISDN',
                'partyId': mobile_number
            },
            'payerMessage': payer_message,
            'payeeNote': f'Booking payment: {external_reference}'
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 202:  # Accepted
                return {
                    'reference_id': reference_id,
                    'status': 'PENDING',
                    'message': 'Payment request sent successfully'
                }
            else:
                raise MobileMoneyError(f"MTN payment request failed: {response.text}")
        except requests.RequestException as e:
            raise MobileMoneyError(f"MTN API connection error: {str(e)}")
    
    def check_payment_status(self, reference_id):
        """Check payment status"""
        # For sandbox, simulate random payment completion
        if self.environment == 'sandbox':
            import random
            statuses = ['SUCCESSFUL', 'PENDING', 'FAILED']
            return {
                'status': random.choice(statuses),
                'reference_id': reference_id,
                'transaction_id': f'mtn_txn_{int(time.time())}'
            }
        
        url = f"{self.base_url}/collection/v1_0/requesttopay/{reference_id}"
        token = self.get_auth_token()
        
        headers = {
            'Authorization': f'Bearer {token}',
            'X-Target-Environment': self.environment,
            'Ocp-Apim-Subscription-Key': self.subscription_key,
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': data.get('status'),
                    'reference_id': reference_id,
                    'transaction_id': data.get('financialTransactionId'),
                    'reason': data.get('reason')
                }
            else:
                raise MobileMoneyError(f"Failed to check MTN payment status: {response.text}")
        except requests.RequestException as e:
            raise MobileMoneyError(f"MTN API connection error: {str(e)}")


class AirtelMoneyService:
    """Airtel Money API Integration"""
    
    def __init__(self):
        # In production, these should be in settings
        self.client_id = getattr(settings, 'AIRTEL_CLIENT_ID', 'sandbox_client')
        self.client_secret = getattr(settings, 'AIRTEL_CLIENT_SECRET', 'sandbox_secret')
        self.base_url = getattr(settings, 'AIRTEL_BASE_URL', 'https://openapi.airtel.africa')
        self.environment = getattr(settings, 'AIRTEL_ENVIRONMENT', 'sandbox')
    
    def generate_reference(self):
        """Generate transaction reference"""
        return f"AIRTEL_{int(time.time())}_{uuid.uuid4().hex[:8].upper()}"
    
    def get_auth_token(self):
        """Get authorization token from Airtel API"""
        url = f"{self.base_url}/auth/oauth2/token"
        headers = {
            'Content-Type': 'application/json'
        }
        
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        
        # For sandbox, simulate token generation
        if self.environment == 'sandbox':
            return 'sandbox_airtel_token_' + str(int(time.time()))
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json().get('access_token')
            else:
                raise MobileMoneyError(f"Failed to get Airtel auth token: {response.text}")
        except requests.RequestException as e:
            raise MobileMoneyError(f"Airtel API connection error: {str(e)}")
    
    def request_payment(self, amount, mobile_number, external_reference, description="Payment for booking"):
        """Request payment from customer's Airtel Money wallet"""
        reference_id = self.generate_reference()
        
        # For sandbox, simulate successful payment request
        if self.environment == 'sandbox':
            return {
                'reference_id': reference_id,
                'status': 'PENDING',
                'message': 'Payment request sent successfully (Sandbox)'
            }
        
        url = f"{self.base_url}/merchant/v1/payments/"
        token = self.get_auth_token()
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'X-Country': 'RW',  # Rwanda
            'X-Currency': 'RWF'
        }
        
        payload = {
            'reference': external_reference,
            'subscriber': {
                'country': 'RW',
                'currency': 'RWF',
                'msisdn': mobile_number
            },
            'transaction': {
                'amount': str(amount),
                'country': 'RW',
                'currency': 'RWF',
                'id': reference_id
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    'reference_id': reference_id,
                    'status': 'PENDING',
                    'message': 'Payment request sent successfully',
                    'airtel_reference': data.get('transaction', {}).get('id')
                }
            else:
                raise MobileMoneyError(f"Airtel payment request failed: {response.text}")
        except requests.RequestException as e:
            raise MobileMoneyError(f"Airtel API connection error: {str(e)}")
    
    def check_payment_status(self, reference_id):
        """Check payment status"""
        # For sandbox, simulate random payment completion
        if self.environment == 'sandbox':
            import random
            statuses = ['TS', 'TF', 'TP']  # Success, Failed, Pending
            status = random.choice(statuses)
            return {
                'status': 'SUCCESSFUL' if status == 'TS' else ('FAILED' if status == 'TF' else 'PENDING'),
                'reference_id': reference_id,
                'transaction_id': f'airtel_txn_{int(time.time())}'
            }
        
        url = f"{self.base_url}/standard/v1/payments/{reference_id}"
        token = self.get_auth_token()
        
        headers = {
            'Authorization': f'Bearer {token}',
            'X-Country': 'RW',
            'X-Currency': 'RWF'
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                transaction = data.get('data', {}).get('transaction', {})
                status_code = transaction.get('status')
                
                # Map Airtel status codes to our status
                status_mapping = {
                    'TS': 'SUCCESSFUL',
                    'TF': 'FAILED',
                    'TP': 'PENDING'
                }
                
                return {
                    'status': status_mapping.get(status_code, 'PENDING'),
                    'reference_id': reference_id,
                    'transaction_id': transaction.get('airtel_money_id'),
                    'reason': transaction.get('status_reason')
                }
            else:
                raise MobileMoneyError(f"Failed to check Airtel payment status: {response.text}")
        except requests.RequestException as e:
            raise MobileMoneyError(f"Airtel API connection error: {str(e)}")


class MobileMoneyManager:
    """Manager class to handle both MTN and Airtel payments"""
    
    def __init__(self):
        self.mtn_service = MTNMoMoService()
        self.airtel_service = AirtelMoneyService()
    
    def request_payment(self, payment_method, amount, mobile_number, external_reference, description=None):
        """Request payment from the appropriate mobile money service"""
        if payment_method == 'mtn_momo':
            return self.mtn_service.request_payment(amount, mobile_number, external_reference, description)
        elif payment_method == 'airtel_money':
            return self.airtel_service.request_payment(amount, mobile_number, external_reference, description)
        else:
            raise MobileMoneyError(f"Unsupported payment method: {payment_method}")
    
    def check_payment_status(self, payment_method, reference_id):
        """Check payment status from the appropriate mobile money service"""
        if payment_method == 'mtn_momo':
            return self.mtn_service.check_payment_status(reference_id)
        elif payment_method == 'airtel_money':
            return self.airtel_service.check_payment_status(reference_id)
        else:
            raise MobileMoneyError(f"Unsupported payment method: {payment_method}")
    
    def validate_mobile_number(self, mobile_number, payment_method):
        """Validate mobile number format for Rwanda"""
        # Remove any spaces or special characters
        clean_number = ''.join(filter(str.isdigit, mobile_number))
        
        # Rwanda mobile numbers can be:
        # - 9 digits starting with 7 (780123456)
        # - 10 digits starting with 07 (0780123456) 
        # - 12 digits starting with 250 (250780123456)
        if len(clean_number) == 9 and clean_number.startswith('7'):
            return f"250{clean_number}"  # Add country code
        elif len(clean_number) == 10 and clean_number.startswith('07'):
            return f"25{clean_number[1:]}"  # Remove 0 and add country code 
        elif len(clean_number) == 12 and clean_number.startswith('250'):
            return clean_number
        else:
            raise MobileMoneyError("Invalid mobile number format. Please use format: 780123456, 0780123456, or 250780123456")
    
    def get_currency_display(self, amount, currency='RWF'):
        """Format currency display"""
        if currency == 'RWF':
            return f"{amount:,} RWF"
        elif currency == 'USD':
            return f"${amount}"
        else:
            return f"{amount} {currency}"