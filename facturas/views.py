from django.shortcuts import render, redirect, get_object_or_404  # <--- AGREGA ESTO AQUÍ
import json
from django.utils import timezone
from .models import Factura
from .utils import revisar_gmail

HORA_INICIO = timezone.now()

# REVISA QUE ESTA FUNCIÓN ESTÉ ESCRITA ASÍ:
def login_view(request):
    if request.method == 'POST':
        request.session['gmail_user'] = request.POST.get('email')
        request.session['gmail_pass'] = request.POST.get('password')
        return redirect('monitor')
    return render(request, 'facturas/login.html')

def monitor_view(request):
    user = request.session.get('gmail_user')
    password = request.session.get('gmail_pass')
    
    if not user or not password:
        return redirect('login')

    if request.headers.get('HX-Request'):
        revisar_gmail(user, password)
        facturas = Factura.objects.filter(fecha_recibido__gt=HORA_INICIO).order_by('-fecha_recibido')
        return render(request, 'facturas/lista_facturas.html', {'facturas': facturas})
    
    return render(request, 'facturas/monitor.html')

def logout_view(request):
    request.session.flush()
    return redirect('login')


def factura_detalle(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    # Convertimos el texto JSON de la base de datos a una lista de Python
    productos = json.loads(factura.detalles_json)
    
    return render(request, 'facturas/detalle.html', {
        'factura': factura,
        'productos': productos
    })