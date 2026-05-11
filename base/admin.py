from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import BDT, User, Evento, Categoria, Scambio, Area

# Register your models here.
admin.site.register(BDT)
admin.site.register(User)
admin.site.register(Evento)
admin.site.register(Categoria)
admin.site.register(Scambio)
admin.site.register(Area)
