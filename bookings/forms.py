from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Booking
from datetime import datetime

class BookingForm(forms.ModelForm):
    check_in = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'min': timezone.now().date().isoformat()
        })
    )
    check_out = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'min': timezone.now().date().isoformat()
        })
    )
    guests = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Number of guests'
        })
    )
    special_requests = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'rows': 3,
            'placeholder': 'Any special requests or notes...'
        })
    )

    class Meta:
        model = Booking
        fields = ['check_in', 'check_out', 'guests', 'special_requests']

    def __init__(self, *args, **kwargs):
        self.listing = kwargs.pop('listing', None)
        super().__init__(*args, **kwargs)
        
        if self.listing:
            self.fields['guests'].widget.attrs['max'] = self.listing.guests

    def save(self, commit=True):
        """Override save to prevent model validation during form processing"""
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance

    def clean_check_in(self):
        check_in = self.cleaned_data.get('check_in')
        if check_in and check_in < timezone.now().date():
            raise ValidationError("Check-in date cannot be in the past")
        return check_in

    def clean_check_out(self):
        check_out = self.cleaned_data.get('check_out')
        check_in = self.cleaned_data.get('check_in')
        
        if check_out and check_in:
            if check_out <= check_in:
                raise ValidationError("Check-out date must be after check-in date")
            
            # Minimum 1 night stay
            if (check_out - check_in).days < 1:
                raise ValidationError("Minimum stay is 1 night")
                
        return check_out

    def clean_guests(self):
        guests = self.cleaned_data.get('guests')
        if self.listing and guests > self.listing.guests:
            raise ValidationError(f"Maximum {self.listing.guests} guests allowed for this property")
        return guests

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        
        if check_in and check_out and self.listing:
            # Check for availability
            overlapping_bookings = Booking.objects.filter(
                listing=self.listing,
                status__in=['confirmed', 'pending'],
                check_in__lt=check_out,
                check_out__gt=check_in
            )
            
            if overlapping_bookings.exists():
                raise ValidationError("These dates are not available. Please choose different dates.")
        
        return cleaned_data


class BookingSearchForm(forms.Form):
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Where are you going?'
        })
    )
    check_in = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'min': timezone.now().date().isoformat()
        })
    )
    check_out = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'min': timezone.now().date().isoformat()
        })
    )
    guests = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Guests'
        })
    )


class BookingCancelForm(forms.Form):
    confirmation = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-red-600 focus:ring-red-500'
        }),
        label="I confirm that I want to cancel this booking"
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500',
            'rows': 3,
            'placeholder': 'Reason for cancellation (optional)...'
        })
    )
