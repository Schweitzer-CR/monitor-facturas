import os
from celery import Celery  # <--- ESTA ES LA LÍNEA QUE DEBES CAMBIAR

# Ajusta el nombre de settings según el nombre de tu proyecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Usar una cadena permite que los workers no tengan que serializar el objeto
app.config_from_object('django.conf:settings', namespace='CELERY')

# Cargar tareas de todos los archivos tasks.py registrados en las apps
app.autodiscover_tasks()