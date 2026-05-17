from django.contrib import admin
from .models import ConfiguracionSistema, Factura

@admin.register(ConfiguracionSistema)
class ConfiguracionAdmin(admin.ModelAdmin):
    # Evita que se creen múltiples configuraciones, solo queremos una
    def has_add_permission(self, request):
        return not ConfiguracionSistema.objects.exists()

admin.site.register(Factura)