from django import forms
from django.core.exceptions import ValidationError
from .models import Review

class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={
            'class': 'sr-only'  # Will be styled with stars
        })
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'rows': 4,
            'placeholder': 'Share your experience with this property...'
        }),
        help_text="Tell other guests about your stay"
    )
    
    class Meta:
        model = Review
        fields = ['rating', 'comment']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.listing = kwargs.pop('listing', None)
        self.booking = kwargs.pop('booking', None)
        super().__init__(*args, **kwargs)
    
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValidationError("Rating must be between 1 and 5 stars")
        except (ValueError, TypeError):
            raise ValidationError("Invalid rating")
        return rating
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check if user already reviewed this listing
        if self.user and self.listing:
            existing_review = Review.objects.filter(
                user=self.user,
                listing=self.listing
            ).exclude(id=self.instance.id if self.instance.id else None)
            
            if existing_review.exists():
                raise ValidationError("You have already reviewed this property.")
        
        return cleaned_data
    
    def save(self, commit=True):
        review = super().save(commit=False)
        if self.user:
            review.user = self.user
        if self.listing:
            review.listing = self.listing
        if self.booking:
            review.booking = self.booking
        
        if commit:
            review.save()
        return review
