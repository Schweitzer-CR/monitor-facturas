# config/urls.py
from django.contrib import admin
from django.urls import path
# REVISA QUE ESTÉN LAS TRES AQUÍ:
from facturas.views import monitor_view, login_view, factura_detalle, logout_view
from django.urls import path
from facturas import views


app_name = 'facturas'
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', monitor_view, name='monitor'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('factura/<int:pk>/', factura_detalle, name='detalle'), # Esta es la ruta del detalle
    path('exportar-excel/', views.exportar_facturas_excel, name='exportar_facturas_excel'),
    path('configurar/', views.guardar_configuracion, name='guardar_config'),
    path('guardar-cliente/', views.guardar_cliente, name='guardar_cliente'),
    path('guardar-config/', views.guardar_configuracion, name='guardar_config'),
    path('eliminar-cliente/<int:pk>/', views.eliminar_cliente, name='eliminar_cliente'),
    
]