import stripe
from django.conf import settings
from django.shortcuts import redirect

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_checkout_session(request):
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': 'Book Purchase',
                },
                'unit_amount': 5000,  # $50.00
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url='http://127.0.0.1:8000/success/',
        cancel_url='http://127.0.0.1:8000/cancel/',
    )
    return redirect(session.url)
