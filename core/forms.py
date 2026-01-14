from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import *

class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'role', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ != "Select":
                field.widget.attrs['class'] = 'form-control'


class ShopItemForm(forms.ModelForm):
    class Meta:
        model = ShopItem
        fields = ['category', 'name', 'description', 'price', 'image', 'status']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter item name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write a short description'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class StudentShopItemForm(forms.ModelForm):
    class Meta:
        model = StudentListedShopItem
        fields = ['category', 'name', 'description', 'price', 'image']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter item name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write a short description'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

        
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['document', 'vendor', 'scheduled_time']  # include vendor if you want student to choose
        widgets = {
            'document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'scheduled_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'vendor': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter vendors to only approved ones
        self.fields['vendor'].queryset = CustomUser.objects.filter(role='vendor', is_approved=True)
        self.fields['vendor'].required = False  # optional, student can let system auto-assign



class OrderUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status', 'scheduled_time']
        widgets = {
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }
