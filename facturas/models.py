from django.db import models

class Factura(models.Model):
    emisor = models.CharField(max_length=255)
    cedula = models.CharField(max_length=20)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    moneda = models.CharField(max_length=10)
    fecha_recibido = models.DateTimeField(auto_now_add=True)
    mensaje_id = models.CharField(max_length=100, unique=True)
    
    # ESTA ES LA LÍNEA QUE TE FALTA:
    detalles_json = models.TextField(default='[]') 

    def __str__(self):
        return f"{self.emisor} - {self.total}"