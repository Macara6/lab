from django.contrib import admin

from .models import *



admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Invoice)
admin.site.register(UserProfile)
admin.site.register(Subscription)
admin.site.register(CashOut)
admin.site.register(CashOutDetail)
admin.site.register(EntryNote)
admin.site.register(EntryNoteDetail)