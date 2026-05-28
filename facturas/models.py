from django.db import models
from django.contrib.auth.models import User

class CuentaCorreoCliente(models.Model):
    usuario_web = models.ForeignKey(User, on_delete=models.CASCADE)
    nombre_cliente = models.CharField(max_length=200)
    correo_origen = models.EmailField(help_text="Correo de Gmail/Office365 del cliente")
    password_aplicacion = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.nombre_cliente} ({self.correo_origen})"

class Factura(models.Model):

    usuario_web = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    cuenta_cliente = models.ForeignKey(CuentaCorreoCliente, on_delete=models.SET_NULL, null=True, blank=True)
    emisor = models.CharField(max_length=255)
    cedula = models.CharField(max_length=20)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    moneda = models.CharField(max_length=10)
    fecha_recibido = models.DateTimeField(auto_now_add=True)
    mensaje_id = models.CharField(max_length=100, unique=True)
    detalles_json = models.TextField(default='[]') 

    def __str__(self):
        return f"{self.emisor} - {self.total}"

class ConfiguracionSistema(models.Model):
    usuario_web = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    meses_historial = models.PositiveIntegerField(default=1)
    correo_destino = models.EmailField(default="asistentecontable@bioingredientscr.com")
    actualizado_en = models.DateTimeField(auto_now=True)