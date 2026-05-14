# config/urls.py
from django.contrib import admin
from django.urls import path
# REVISA QUE ESTÉN LAS TRES AQUÍ:
from facturas.views import monitor_view, login_view, factura_detalle, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', monitor_view, name='monitor'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('factura/<int:pk>/', factura_detalle, name='detalle'), # Esta es la ruta del detalle
]