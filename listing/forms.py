from django import forms
from .models import Listing

class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = [
            'title',
            'description',
            'location',
            'price_per_night',
            'property_type',
            'guests',
            'bedrooms',
            'beds',
            'bathrooms',
            'image',
            'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control w-[90%] p-2',
                'placeholder': 'Enter listing title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control w-[90%] p-2',
                'placeholder': 'Describe the property...',
                'rows': 4
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control w-[90%] p-2',
                'placeholder': 'Location (e.g., Kigali, Rwanda)'
            }),
            'price_per_night': forms.NumberInput(attrs={
                'class': 'form-control w-[90%] pd-2',
                'placeholder': 'Price per night',
                'min': '0'
            }),
            'property_type': forms.Select(attrs={
                'class': 'form-control w-[90%] p-2'
            }),
            'guests': forms.NumberInput(attrs={
                'class': 'form-control w-[90%] p-2',
                'min': 1
            }),
            'bedrooms': forms.NumberInput(attrs={
                'class': 'form-control w-[90%] p-2',
                'min': 0
            }),
            'beds': forms.NumberInput(attrs={
                'class': 'form-control w-[90%] p-2',
                'min': 0
            }),
            'bathrooms': forms.NumberInput(attrs={
                'class': 'form-control w-[90%] p-2',
                'min': 0
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control w-[90%] p-2'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_price_per_night(self):
        price = self.cleaned_data.get('price_per_night')
        if price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        return price

    def clean_guests(self):
        guests = self.cleaned_data.get('guests')
        if guests < 1:
            raise forms.ValidationError("At least one guest must be allowed.")
        return guests
