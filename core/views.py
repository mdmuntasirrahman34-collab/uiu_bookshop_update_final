from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .forms import *
from .models import *
from django.contrib.auth.views import LoginView
from django.db.models import Prefetch
import stripe
from django.conf import settings
from django.db.models import Prefetch, F, Sum
from django.urls import reverse

stripe.api_key = settings.STRIPE_SECRET_KEY

def vendor_required(view_func):
    """Decorator to ensure only approved vendors can access"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.role != "vendor" or not request.user.is_approved:
            return HttpResponseForbidden("You are not authorized to access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper

def student_required(view_func):
    """Decorator to ensure only approved vendors can access"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.role != "student":
            return HttpResponseForbidden("You are not authorized to access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper


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


def contact(request):
    if request.method == "POST":
        
        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")
        
        from django.contrib import messages
        messages.success(request, "Your message has been sent! We'll get back to you soon.")
        return render(request, "core/contact.html")
    return render(request, "core/contact.html")


def about(request):
    team_members = [
        {
            "name": "Md Muntasir Rahman",
            "id": "011211137",
            "image": "images/team/Md Muntasir Rahman ID-011211137.jpg"
        },
        {
            "name": "Shahin Shikder Dipu",
            "id": "011202095",
            "image": "images/team/Name-Shahin Shikder Dipu  ID-011202095.jpg"
        },
        {
            "name": "Riad Hasan",
            "id": "011202290",
            "image": "images/team/Riad Hasan ID-011202290.jpg"
        }
    ]
    return render(request, "core/about.html", {"team_members": team_members})

def home(request):
    
    features = [
        {
            "title": "Fast Printing",
            "description": "Get your documents printed quickly with same-day service.",
            "icon": "bi-speedometer2"
        },
        {
            "title": "High Quality",
            "description": "Professional quality prints with vibrant colors and sharp text.",
            "icon": "bi-brush"
        },
        {
            "title": "Affordable Prices",
            "description": "Competitive pricing for students and businesses alike.",
            "icon": "bi-cash-stack"
        },
        {
            "title": "Secure Handling",
            "description": "Your documents are handled safely and confidentially.",
            "icon": "bi-shield-lock"
        },
    ]
    return render(request, "core/home.html", {"features": features})



def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if user.role == "student":
                user.is_approved = True  
            else:
                user.is_approved = False 
            user.save()
            messages.success(request, "Registration successful. Please wait for approval if you're a vendor.")
            return redirect("login")
    else:
        form = CustomUserCreationForm()
    return render(request, "accounts/register.html", {"form": form})

# Login view with role redirect
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



@login_required
def student_dashboard(request):
    if request.user.role != "student":
        return redirect("vendor_dashboard")

    total_orders = request.user.orders.count()
    in_progress = request.user.orders.filter(status="in_progress").count()
    completed = request.user.orders.filter(status="done").count()

    return render(request, "student_dashboard.html", {
        "total_orders": total_orders,
        "in_progress": in_progress,
        "completed": completed,
    })


@login_required
def vendor_dashboard(request):
    if request.user.role != "vendor":
        return redirect("student_dashboard")

    total_orders = request.user.vendor_orders.count()
    in_progress = request.user.vendor_orders.filter(status="in_progress").count()
    completed = request.user.vendor_orders.filter(status="done").count()

    return render(request, "vendor_dashboard.html", {
        "total_orders": total_orders,
        "in_progress": in_progress,
        "completed": completed,
    })



def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')


@login_required
def create_order(request):
    if request.user.role != 'student':
        return redirect('vendor_dashboard')

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


# @login_required
# def vendor_orders(request):
#     if request.user.role != 'vendor':
#         return redirect('student_dashboard')

#     # Show orders assigned to vendor OR unassigned pending orders
#     orders = Order.objects.filter(
#         models.Q(vendor=request.user) | models.Q(vendor__isnull=True, status='pending')
#     ).order_by('-created_at')

#     return render(request, 'core/vendor_orders.html', {'orders': orders})

# Student sees orders
@login_required
@student_required
def student_orders(request):
    
    shop_orders = ShopOrder.objects.filter(buyer=request.user).select_related("item")
    print_orders = Order.objects.filter(student=request.user)

    context = {
        "shop_orders": shop_orders,
        "print_orders": print_orders,
    }
    return render(request, "store/student_orders.html", context)


@login_required
def update_order(request, order_id):
    if request.user.role != 'vendor':
        return redirect('student_dashboard')

    order = get_object_or_404(Order, id=order_id)

    # assign order if not assigned
    if order.vendor is None:
        order.vendor = request.user
        order.save()

    # allow vendor to update status
    if request.method == 'POST':
        form = OrderUpdateForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect('vendor_orders')
    else:
        form = OrderUpdateForm(instance=order)

    return render(request, 'core/update_order.html', {'form': form, 'order': order})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_approve_vendors(request):
    # Get vendors waiting for approval
    pending_vendors = CustomUser.objects.filter(role='vendor', is_approved=False)

    if request.method == "POST":
        vendor_id = request.POST.get("vendor_id")
        action = request.POST.get("action")

        vendor = CustomUser.objects.get(id=vendor_id)
        if action == "approve":
            vendor.is_approved = True
            vendor.save()
        elif action == "reject":
            vendor.delete()

        return redirect('admin_approve_vendors')

    return render(request, 'core/admin_approve_vendors.html', {'pending_vendors': pending_vendors})


@login_required
@vendor_required
def my_store(request):
    items = ShopItem.objects.filter(vendor=request.user)
    return render(request, "store/my_store.html", {"items": items})

@login_required
@student_required
def student_my_store(request):
    items = StudentListedShopItem.objects.filter(student_vendor=request.user)
    return render(request, "store/student_my_store.html", {"items": items})


@login_required
@vendor_required
def add_item(request):
    if request.method == "POST":
        form = ShopItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.vendor = request.user
            item.save()
            return redirect("my_store")
    else:
        form = ShopItemForm()
    return render(request, "store/add_item.html", {"form": form})

@login_required
@student_required
def student_add_item(request):
    if request.method == "POST":
        form = StudentShopItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.student_vendor = request.user
            item.status = "active"
            item.save()
            return redirect("student_my_store")
    else:
        form = StudentShopItemForm()
    return render(request, "store/add_item.html", {"form": form})


@login_required
@vendor_required
def edit_item(request, item_id):
    item = get_object_or_404(ShopItem, id=item_id, vendor=request.user)
    if request.method == "POST":
        form = ShopItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect("my_store")
    else:
        form = ShopItemForm(instance=item)
    return render(request, "store/edit_item.html", {"form": form, "item": item})


@login_required
@vendor_required
def delete_item(request, item_id):
    item = get_object_or_404(ShopItem, id=item_id, vendor=request.user)
    if request.method == "POST":
        item.delete()
        return redirect("my_store")
    return render(request, "store/delete_item.html", {"item": item})

@login_required
@student_required
def student_delete_item(request, item_id):
    item = get_object_or_404(StudentListedShopItem, id=item_id, student_vendor=request.user)
    if request.method == "POST":
        item.delete()
        return redirect("student_my_store")
    return render(request, "store/delete_item.html", {"item": item})



@login_required
@vendor_required
def toggle_item_status(request, item_id):
    item = get_object_or_404(ShopItem, id=item_id, vendor=request.user)
    item.status = "inactive" if item.status == "active" else "active"
    item.save()
    return redirect("my_store")


def shop_view(request):
    categories = Category.objects.prefetch_related("items").all()
    return render(request, "store/shop.html", {"categories": categories})

def student_shop_view(request):
    if not request.user.is_authenticated:
        student_items_prefetch = Prefetch(
            "student_items",
            queryset=StudentListedShopItem.objects.filter(status="active").select_related("student_vendor", "approved_by")
        )
    else:
        # active_items = Prefetch(
        #     "student_items",
        #     queryset=StudentListedShopItem.objects.filter(status="active").select_related("student_vendor", "approved_by")
        # )
        # categories = Category.objects.prefetch_related(active_items)
        # return render(request, "store/student_shop.html", {"categories": categories})

        if request.user.role == "vendor":
            # Vendors see inactive student items
            student_items_prefetch = Prefetch(
                "student_items",
                queryset=StudentListedShopItem.objects.filter(status="inactive").select_related("student_vendor")
            )
        else:
            # Students see only active items
            student_items_prefetch = Prefetch(
                "student_items",
                queryset=StudentListedShopItem.objects.filter(status="active").select_related("student_vendor", "approved_by")
            )

    categories = Category.objects.prefetch_related(student_items_prefetch)
    return render(request, "store/student_shop.html", {"categories": categories})

@login_required
def approve_student_item(request, item_id):
    if request.user.role != "vendor":
        return redirect("studentshop")

    item = get_object_or_404(StudentListedShopItem, id=item_id)
    item.status = "active"
    item.approved_by = request.user
    item.save()

    return redirect("studentshop")



# @login_required
# def order_item(request, item_id):
#     if request.user.role != 'student':
#         return redirect('home')
#     item = get_object_or_404(ShopItem, id=item_id, status="active")
#     print(item)
#     if request.method == "POST":
#         quantity = int(request.POST.get("quantity", 1))
#         ShopOrder.objects.create(buyer=request.user, item=item, quantity=quantity)
#         return redirect("shop")  # after ordering, go back to shop
#     return render(request, "store/order_item.html", {"item": item})

@login_required
def order_item(request, item_id):
    if request.user.role != 'student':
        return redirect('home')

    item = get_object_or_404(StudentListedShopItem, id=item_id, status="active")

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))
        # Create the order
        order = StudentShopOrder.objects.create(
            buyer=request.user,
            item=item,
            quantity=quantity
        )

        # ✅ Redirect to the new delivery details form
        return redirect("delivery_details", order_id=order.id)

    return render(request, "store/order_item.html", {"item": item})



@login_required
def vendor_orders(request):
    if request.user.role != 'vendor':
        return redirect('student_orders')

    print_orders = Order.objects.filter(
        models.Q(vendor=request.user) | models.Q(vendor__isnull=True, status='pending')
    ).order_by('-created_at')

    shop_orders = ShopOrder.objects.filter(item__vendor=request.user).select_related("item", "buyer")

    return render(request, 'store/vendor_orders2.html', {
        'print_orders': print_orders,
        'shop_orders': shop_orders,
    })

@login_required
def student_shop_orders(request):
    if request.user.role != 'student':
        return redirect('vendor_orders')


    shop_orders = StudentShopOrder.objects.filter(item__student_vendor=request.user).select_related("item", "buyer")

    return render(request, 'store/student_vendor_orders.html', {
        'shop_orders': shop_orders,
    })


@login_required
@vendor_required
def update_order_status(request, order_type, order_id):
    if order_type == "shop":
        order = get_object_or_404(ShopOrder, id=order_id, item__vendor=request.user)
        valid_statuses = dict(ShopOrder.STATUS_CHOICES)
    elif order_type == "print":
        order = get_object_or_404(Order, id=order_id, vendor=request.user)
        valid_statuses = dict(Order.STATUS_CHOICES)
    else:
        return redirect("vendor_orders")

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in valid_statuses:
            order.status = new_status
            order.save()
        return redirect("vendor_orders")
    
@login_required
@student_required
def update_student_order_status(request, order_type, order_id):
    print("Here")

    order = get_object_or_404(StudentShopOrder, id=order_id, item__student_vendor=request.user)
    valid_statuses = dict(StudentShopOrder.STATUS_CHOICES)


    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in valid_statuses:
            order.status = new_status
            order.save()
        return redirect("student_vendor_orders")

def test_view(request):
    #db pull update, crud

    return render(request, "test_page.html")



@login_required
def delivery_details_view(request, order_id):
    order = get_object_or_404(StudentShopOrder, id=order_id, buyer=request.user)
    
    if request.method == "POST":
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')

        delivery_info = f"Name: {name}\nPhone: {phone}\nAddress: {address}"
        order.delivery_details = delivery_info
        order.save()

        # Redirect to Stripe checkout
        return render(request, "store/order_success.html")

    return render(request, "store/delivery_details.html", {"order": order})

@login_required
def create_checkout_session(request, order_id):
    order = get_object_or_404(ShopOrder, id=order_id, buyer=request.user)
    YOUR_DOMAIN = "http://127.0.0.1:8000"

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'bdt', 
                'product_data': {
                    'name': order.item.name,
                },
                'unit_amount': int(order.item.price * 100),
            },
            'quantity': order.quantity,
        }],
        metadata={
            "order_id": order.id,
        },
        mode='payment',
        success_url=YOUR_DOMAIN + '/payment-success/?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=YOUR_DOMAIN + '/payment-cancel/',
        client_reference_id=str(order.id),
    )

    
    order.stripe_session_id = checkout_session.id
    order.save(update_fields=["stripe_session_id"])

    return JsonResponse({'id': checkout_session.id})

# @login_required
# def payment_success(request):
#     session_id = request.GET.get("session_id")
#     if not session_id:
#         return HttpResponse("No session_id provided", status=400)

#     session = stripe.checkout.Session.retrieve(session_id)

#     if session.payment_status == "paid":
#         order_id = session.client_reference_id
#         ShopOrder.objects.filter(id=order_id).update(payment_status="Paid")
#     return render(request, "store/payment_success.html")

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
        # Get user and cart from session metadata
        user_id = session.metadata.get("user_id")
        user = CustomUser.objects.get(id=user_id)
        cart = Cart.objects.get(user=user)
        
        # Get delivery details from user's session
        delivery_details_dict = request.session.get('delivery_details', {})
        delivery_info = (
            f"Name: {delivery_details_dict.get('name', 'N/A')}\n"
            f"Phone: {delivery_details_dict.get('phone', 'N/A')}\n"
            f"Address: {delivery_details_dict.get('address', 'N/A')}"
        )

        # Create a separate ShopOrder for each item in the cart
        for cart_item in cart.items.all():
            ShopOrder.objects.create(
                buyer=user,
                item=cart_item.item,
                quantity=cart_item.quantity,
                status="pending",  # Set initial status
                payment_status="Paid",
                delivery_details=delivery_info,
                stripe_session_id=session_id
            )
        
        # Clear the cart and delivery details from session
        cart.items.all().delete()
        if 'delivery_details' in request.session:
            del request.session['delivery_details']
            
        return render(request, "store/payment_success.html")

    else:
        messages.error(request, "Payment was not successful.")
        return redirect("payment_cancel")

@login_required
def payment_cancel(request):
    return render(request, "store/payment_cancel.html")







# @login_required
# @student_required
# def add_to_cart(request, item_id):
#     """Adds a ShopItem to the student's cart."""
#     item = get_object_or_404(ShopItem, id=item_id, status="active")
    
#     # Get or create the user's cart
#     cart, _ = Cart.objects.get_or_create(user=request.user)
    
#     # Get or create the cart item
#     cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
    
#     if not created:
#         # If item is already in cart, increment quantity
#         cart_item.quantity = F('quantity') + 1
#         cart_item.save()
        
#     messages.success(request, f"'{item.name}' was added to your cart.")
#     return redirect("shop")

@login_required
@student_required
def add_to_cart(request, item_id):
    """Adds a ShopItem to the student's cart."""
    item = get_object_or_404(ShopItem, id=item_id, status="active")
    
    # Get or create the user's cart
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    # Get or create the cart item
    cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
    
    if not created:
        # If item is already in cart, increment quantity
        cart_item.quantity = F('quantity') + 1
        cart_item.save()
        # Refresh from DB to get the actual new quantity after F() expression
        cart_item.refresh_from_db() 
    
    # --- NEW AJAX HANDLING ---
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if is_ajax:
        # Re-calculate the total cart count
        count_data = cart.items.aggregate(total_quantity=Sum('quantity'))
        new_cart_count = count_data['total_quantity'] or 0
        
        return JsonResponse({
            'success': True,
            'message': f"'{item.name}' was added to your cart.",
            'new_cart_count': new_cart_count
        })
    # --- END NEW AJAX HANDLING ---
        
    # This is the original response for non-JS users
    messages.success(request, f"'{item.name}' was added to your cart.")
    return redirect("shop")

@login_required
@student_required
def view_cart(request):
    """Displays the user's cart."""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, "store/view_cart.html", {"cart": cart})

@login_required
@student_required
def remove_from_cart(request, cart_item_id):
    """Removes an item from the cart."""
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
    item_name = cart_item.item.name
    cart_item.delete()
    messages.success(request, f"'{item_name}' was removed from your cart.")
    return redirect("view_cart")

@login_required
@student_required
def cart_checkout(request):
    """Displays the delivery details form for a cart checkout."""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    if cart.items.count() == 0:
        messages.error(request, "Your cart is empty. Please add items before checking out.")
        return redirect("shop")
        
    if request.method == "POST":
        # Save delivery details in the session to pass to Stripe
        request.session['delivery_details'] = {
            'name': request.POST.get('name'),
            'phone': request.POST.get('phone'),
            'address': request.POST.get('address'),
        }
        # Redirect to the payment page
        return render(request, "store/payment_cart.html", {
            "cart": cart,
            "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY
        })
        
    return render(request, "store/checkout.html", {"cart": cart})

@login_required
@student_required
def create_cart_checkout_session(request):
    """Creates a Stripe checkout session for the entire cart."""
    cart = get_object_or_404(Cart, user=request.user)
    YOUR_DOMAIN = "http://127.0.0.1:8000"

    # Build the list of line items from the cart
    line_items = []
    for cart_item in cart.items.all():
        line_items.append({
            'price_data': {
                'currency': 'bdt',
                'product_data': {
                    'name': cart_item.item.name,
                },
                'unit_amount': int(cart_item.item.price * 100),
            },
            'quantity': cart_item.quantity,
        })

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        metadata={
            "user_id": request.user.id, # Pass user_id to identify on success
        },
        mode='payment',
        success_url=YOUR_DOMAIN + '/payment-success/?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=YOUR_DOMAIN + '/payment-cancel/',
    )

    return JsonResponse({'id': checkout_session.id})