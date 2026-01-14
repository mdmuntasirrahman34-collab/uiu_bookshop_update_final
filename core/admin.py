from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {"fields": ("role", "is_approved")}),
    )
    list_display = ("username", "email", "role", "is_approved", "is_staff")

admin.site.register(CustomUser, CustomUserAdmin)

admin.site.register(Category)
admin.site.register(Order)
admin.site.register(ShopItem)
admin.site.register(StudentListedShopItem)
admin.site.register(ShopOrder)
