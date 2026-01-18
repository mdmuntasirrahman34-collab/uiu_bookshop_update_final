from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .forms import *
from .models import *
from django.contrib.auth.views import LoginView
from django.db.models import Prefetch, F, Sum
from django.urls import reverse
import stripe
from django.conf import settings

# ----------------------------
# Stripe Setup (Safe)
# ----------------------------
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
if not stripe.api_key:
    raise Exception("STRIPE_SECRET_KEY is missing in settings.py")

# ----------------------------
# Decorators
# ----------------------------
def vendor_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.role != "vendor" or not request.user.is_approved:
            return HttpResponseForbidden("You are not authorized to access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper

def student_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.role != "student":
            return HttpResponseForbidden("You are not authorized to access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper

# ----------------------------
# Login & Registration
# ----------------------------
class CustomLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser:
            return '/custom-admin/approve-vendors/'
        elif user.role == "student":
            return "/student/dashboard/"
        elif user.role == "vendor":
            return "/vendor/dashboard/"
        return "/"

def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_approved = True if user.role == "student" else False
            user.save()
            messages.success(request, "Registration successful. Please wait for approval if you're a vendor.")
            return redirect("login")
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/register.html", {"form": form})

def custom_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.can_login():
                login(request, user)
                if user.role == "student":
                    return redirect("student_dashboard")
                elif user.role == "vendor":
                    return redirect("vendor_dashboard")
            else:
                messages.error(request, "Your account is not approved yet.")
        else:
            messages.error(request, "Invalid credentials")
    return render(request, "accounts/login.html")

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')

# ----------------------------
# Static Pages
# ----------------------------
def home(request):
    features = [
        {"title": "Fast Printing", "description": "Get your documents printed quickly with same-day service.", "icon": "bi-speedometer2"},
        {"title": "High Quality", "description": "Professional quality prints with vibrant colors and sharp text.", "icon": "bi-brush"},
        {"title": "Affordable Prices", "description": "Competitive pricing for students and businesses alike.", "icon": "bi-cash-stack"},
        {"title": "Secure Handling", "description": "Your documents are handled safely and confidentially.", "icon": "bi-shield-lock"},
    ]
    return render(request, "core/home.html", {"features": features})

def about(request):
    team_members = [
        {"name": "Md Muntasir Rahman", "id": "011211137", "image": "images/team/Md Muntasir Rahman ID-011211137.jpg"},
        {"name": "Shahin Shikder Dipu", "id": "011202095", "image": "images/team/Name-Shahin Shikder Dipu  ID-011202095.jpg"},
        {"name": "Riad Hasan", "id": "011202290", "image": "images/team/Riad Hasan ID-011202290.jpg"}
    ]
    return render(request, "core/about.html", {"team_members": team_members})

def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")
        messages.success(request, "Your message has been sent! We'll get back to you soon.")
    return render(request, "core/contact.html")

# ----------------------------
# Dashboards
# ----------------------------
@login_required
@student_required
def student_dashboard(request):
    total_orders = request.user.orders.count()
    in_progress = request.user.orders.filter(status="in_progress").count()
    completed = request.user.orders.filter(status="done").count()
    return render(request, "student_dashboard.html", {"total_orders": total_orders, "in_progress": in_progress, "completed": completed})

@login_required
@vendor_required
def vendor_dashboard(request):
    total_orders = request.user.vendor_orders.count()
    in_progress = request.user.vendor_orders.filter(status="in_progress").count()
    completed = request.user.vendor_orders.filter(status="done").count()
    return render(request, "vendor_dashboard.html", {"total_orders": total_orders, "in_progress": in_progress, "completed": completed})

# ----------------------------
# Orders & Checkout
# ----------------------------
@login_required
@student_required
def create_order(request):
    if request.method == 'POST':
        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)
            order.student = request.user
            if not order.vendor:
                order.save()
                order.assign_random_vendor()
            else:
                order.save()
            return redirect('student_orders')
    else:
        form = OrderForm()
    return render(request, 'core/create_order.html', {'form': form})

@login_required
@student_required
def student_orders(request):
    shop_orders = ShopOrder.objects.filter(buyer=request.user).select_related("item")
    print_orders = Order.objects.filter(student=request.user)
    return render(request, "store/student_orders.html", {"shop_orders": shop_orders, "print_orders": print_orders})

@login_required
@vendor_required
def vendor_orders(request):
    print_orders = Order.objects.filter(models.Q(vendor=request.user) | models.Q(vendor__isnull=True, status='pending')).order_by('-created_at')
    shop_orders = ShopOrder.objects.filter(item__vendor=request.user).select_related("item", "buyer")
    return render(request, 'store/vendor_orders2.html', {'print_orders': print_orders, 'shop_orders': shop_orders})

# ----------------------------
# Stripe Checkout
# ----------------------------
@login_required
def create_checkout_session(request, order_id):
    order = get_object_or_404(ShopOrder, id=order_id, buyer=request.user)
    YOUR_DOMAIN = "http://127.0.0.1:8000"

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'bdt',
                'product_data': {'name': order.item.name},
                'unit_amount': int(order.item.price * 100),
            },
            'quantity': order.quantity,
        }],
        metadata={"order_id": order.id},
        mode='payment',
        success_url=YOUR_DOMAIN + '/payment-success/?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=YOUR_DOMAIN + '/payment-cancel/',
        client_reference_id=str(order.id),
    )

    order.stripe_session_id = checkout_session.id
    order.save(update_fields=["stripe_session_id"])
    return JsonResponse({'id': checkout_session.id})

@login_required
def payment_success(request):
    session_id = request.GET.get("session_id")
    if not session_id:
        return HttpResponse("No session_id provided", status=400)
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:
        messages.error(request, f"Invalid session: {e}")
        return redirect("home")
    if session.payment_status == "paid":
        return render(request, "store/payment_success.html")
    else:
        messages.error(request, "Payment was not successful.")
        return redirect("payment_cancel")

@login_required
def payment_cancel(request):
    return render(request, "store/payment_cancel.html")

# ----------------------------
# Cart Management
# ----------------------------
@login_required
@student_required
def add_to_cart(request, item_id):
    item = get_object_or_404(ShopItem, id=item_id, status="active")
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
    if not created:
        cart_item.quantity = F('quantity') + 1
        cart_item.save()
        cart_item.refresh_from_db()
    messages.success(request, f"'{item.name}' was added to your cart.")
    return redirect("shop")

@login_required
@student_required
def view_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, "store/view_cart.html", {"cart": cart})

@login_required
@student_required
def remove_from_cart(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect("view_cart")

@login_required
@student_required
def cart_checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    if cart.items.count() == 0:
        messages.error(request, "Your cart is empty.")
        return redirect("shop")
    if request.method == "POST":
        request.session['delivery_details'] = {
            'name': request.POST.get('name'),
            'phone': request.POST.get('phone'),
            'address': request.POST.get('address'),
        }
        return render(request, "store/payment_cart.html", {"cart": cart, "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY})
    return render(request, "store/checkout.html", {"cart": cart})

@login_required
@student_required
def create_cart_checkout_session(request):
    cart = get_object_or_404(Cart, user=request.user)
    YOUR_DOMAIN = "http://127.0.0.1:8000"
    line_items = [{
        'price_data': {
            'currency': 'bdt',
            'product_data': {'name': ci.item.name},
            'unit_amount': int(ci.item.price * 100),
        },
        'quantity': ci.quantity,
    } for ci in cart.items.all()]

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        metadata={"user_id": request.user.id},
        mode='payment',
        success_url=YOUR_DOMAIN + '/payment-success/?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=YOUR_DOMAIN + '/payment-cancel/',
    )

    return JsonResponse({'id': checkout_session.id})
