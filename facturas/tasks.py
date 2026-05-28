from celery import shared_task         # <--- CORRECTO: Importamos de la librería
from config.celery import app
from django.contrib.auth.models import User
from .models import CuentaCorreoCliente, ConfiguracionSistema
from .utils import procesar_correos_usuario

@shared_task
def sincronizar_todos_los_clientes():
    """
    Esta tarea se ejecutará automáticamente cada X tiempo por Celery Beat.
    Itera sobre todos los usuarios del sistema y procesa sus correos.
    """
    # Obtenemos todos los usuarios que tienen al menos una cuenta configurada
    usuarios = User.objects.filter(cuentacorreocliente__isnull=False).distinct()
    
    for usuario in usuarios:
        try:
            print(f"🔄 Iniciando sincronización para el usuario: {usuario.username}")
            # Llamamos a tu lógica que ya tienes en utils.py
            # Nota: Asegúrate de que utils.py siga importando correctamente los modelos
            procesar_correos_usuario(usuario)
            print(f"✅ Sincronización completada para: {usuario.username}")
        except Exception as e:
            print(f"❌ Error crítico procesando usuario {usuario.username}: {e}")

# Si en el futuro quieres procesar un usuario específico bajo demanda:
@shared_task
def sincronizar_usuario_especifico(usuario_id):
    usuario = User.objects.get(id=usuario_id)
    procesar_correos_usuario(usuario)