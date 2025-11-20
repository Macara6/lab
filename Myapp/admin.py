from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import *



admin.site.register(CustomUser, UserAdmin)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(StockHistory)
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
admin.site.register(UserProfile)
admin.site.register(SecretAccessKey)
admin.site.register(PasswordResetToken)
admin.site.register(Subscription)
admin.site.register(CashOut)
admin.site.register(CashOutDetail)
admin.site.register(EntryNote)
admin.site.register(EntryNoteDetail)
admin.site.register(DepotProduct)
admin.site.register(ExitDepot)
