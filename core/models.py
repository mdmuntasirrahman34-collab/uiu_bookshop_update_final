
import random
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings



class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('vendor', 'Vendor'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    is_approved = models.BooleanField(default=False)  # Only matters for vendors

    def can_login(self):
        if self.role == 'vendor':
            return self.is_approved
        return True
    

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name
    

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    )

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'vendor', 'is_approved': True},
        related_name='vendor_orders'
    )
    document = models.FileField(upload_to='orders/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def assign_random_vendor(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        vendors = User.objects.filter(role='vendor', is_approved=True)
        if vendors.exists():
            self.vendor = random.choice(vendors)
            self.save()

class ShopItem(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shop_items")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="shop_items/", blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='inactive')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.category})"
    

class StudentListedShopItem(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    student_vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_shop_items"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="approved_student_items"
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="student_items")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="student_shop_items/", blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='inactive')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.category})"

    
class ShopOrder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('delivered', 'Delivered'),
        ('done', 'Done'),
        ('canceled', 'Canceled'),
    )
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shop_orders")
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE, related_name="shop_orders")
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    delivery_details = models.TextField(blank=True, null=True)  
    payment_status = models.CharField(max_length=20, default="unpaid")
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)


    def total_price(self):
        return self.quantity * self.item.price

    def __str__(self):
        return f"Order {self.id} by {self.buyer.username}"
    
class StudentShopOrder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('delivered', 'Delivered'),
        ('done', 'Done'),
        ('canceled', 'Canceled'),
    )
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shop_orders2")
    item = models.ForeignKey(StudentListedShopItem, on_delete=models.CASCADE, related_name="shop_orders2")
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    delivery_details = models.TextField(blank=True, null=True)  
    payment_status = models.CharField(max_length=20, default="unpaid")
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)


    def total_price(self):
        return self.quantity * self.item.price

    def __str__(self):
        return f"Order {self.id} by {self.buyer.username}"
    

class Cart(models.Model):
    """A cart belonging to a specific student."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
        limit_choices_to={'role': 'student'}
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        """Calculates the total price of all items in the cart."""
        return sum(item.total_price for item in self.items.all())

    def __str__(self):
        return f"Cart for {self.user.username}"

class CartItem(models.Model):
    """An item within a cart."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        """Calculates the total price for this cart item."""
        return self.item.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.item.name} in {self.cart.user.username}'s cart"