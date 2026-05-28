from django.contrib import admin
from .models import ConfiguracionSistema, Factura, CuentaCorreoCliente

@admin.register(ConfiguracionSistema)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ('usuario_web', 'correo_destino', 'meses_historial')
    
    # Evita que se creen múltiples configuraciones, solo queremos una
    def has_add_permission(self, request):
        return not ConfiguracionSistema.objects.exists()

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    # Columnas que verás en la lista
    list_display = ('emisor', 'total', 'moneda', 'fecha_recibido', 'cuenta_cliente')
    
    # Filtros laterales rápidos
    list_filter = ('moneda', 'fecha_recibido', 'cuenta_cliente')
    
    # Buscador para encontrar facturas por nombre o cédula
    search_fields = ('emisor', 'cedula')
    
    # Ordenar por defecto de más reciente a más antigua
    ordering = ('-fecha_recibido',)

@admin.register(CuentaCorreoCliente)
class CuentaCorreoAdmin(admin.ModelAdmin):
    list_display = ('nombre_cliente', 'correo_origen')
    search_fields = ('nombre_cliente', 'correo_origen')