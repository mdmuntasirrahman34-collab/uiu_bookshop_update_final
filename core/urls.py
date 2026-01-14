from django.urls import path
from core.views import *
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path('', home, name='home'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register, name='register'),
    path('contact/', contact, name='contact'),
    path('about/', about, name='about'),


    path('student/dashboard/', student_dashboard, name='student_dashboard'),
    path('vendor/dashboard/', vendor_dashboard, name='vendor_dashboard'),


    path('orders/create/', create_order, name='create_order'),
    path('orders/student/', student_orders, name='student_orders'),
    # path('orders/vendor/', vendor_orders, name='vendor_orders'),
    path('orders/vendor/update/<int:order_id>/', update_order, name='update_order'),
    path('custom-admin/approve-vendors/', admin_approve_vendors, name='admin_approve_vendors'),

    path('shop/', shop_view, name='shop'),
    path('student-shop/', student_shop_view, name='studentshop'),
    path("student-store/add/", student_add_item, name="student_add_item"),

    path('order-item/<int:item_id>/', order_item, name='order_item'),
    path('vendor-orders/', vendor_orders, name='vendor_orders'),
    path('student-vendor-orders/', student_shop_orders, name='student_vendor_orders'),
    path("my-orders/", student_orders, name="student_orders"),
    path('update-order-status/<str:order_type>/<int:order_id>', update_order_status, name='update_order_status'),
    path('update-student-order-status/<str:order_type>/<int:order_id>', update_student_order_status, name='update_student_order_status'),
    # path('update-order-status/<int:item_id>/', update_order_status, name='update_order_status'),
    
    path("my-store/", my_store, name="my_store"),
    path("my-student-store/", student_my_store, name="student_my_store"),
    path("my-store/add/", add_item, name="add_item"),
    path("my-store/toggle/<int:item_id>/", toggle_item_status, name="toggle_item_status"),
    path("my-store/edit/<int:item_id>/", edit_item, name="edit_item"),
    path("my-store/delete/<int:item_id>/", delete_item, name="delete_item"),
    path("my-student-store/delete/<int:item_id>/", student_delete_item, name="student_delete_item"),
    path("my-store/toggle/<int:item_id>/", toggle_item_status, name="toggle_item_status"),



    path("approve-item/<int:item_id>/", approve_student_item, name="approve_student_item"),
    path('order/<int:order_id>/delivery/', delivery_details_view, name='delivery_details'),


    path('create-checkout-session/<int:order_id>/', create_checkout_session, name='create_checkout_session'),
    path('payment-success/', payment_success, name='payment_success'),
    path('payment-cancel/', payment_cancel, name='payment_cancel'),

    # path('stripe/webhook/', stripe_webhook, name='stripe_webhook'),

    path('cart/', view_cart, name='view_cart'),
    path('cart/add/<int:item_id>/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:cart_item_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/checkout/', cart_checkout, name='cart_checkout'),

    path('create-cart-checkout-session/', create_cart_checkout_session, name='create_cart_checkout_session'),

]
