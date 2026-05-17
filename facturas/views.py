from django.shortcuts import render, redirect, get_object_or_404  # <--- AGREGA ESTO AQUÍ
import json
from django.utils import timezone
from .models import Factura
from .utils import revisar_gmail
import openpyxl
from django.http import HttpResponse
from .models import Factura # Asegúrate de que este sea el nombre de tu modelo
from django.shortcuts import render, redirect
# Asegúrate de incluir ConfiguracionSistema aquí
from .models import Factura, ConfiguracionSistema

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


def exportar_facturas_excel(request):
    # Crear un nuevo libro de Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte de Facturas"

    # Definir los encabezados del Excel
    headers = ['Fecha Recibido', 'Emisor', 'Cédula', 'Moneda', 'Total']
    ws.append(headers)

    # Obtener los datos de la base de datos
    facturas = Factura.objects.all()

    for factura in facturas:
        # Usamos los nombres exactos de tu clase Factura
        ws.append([
            factura.fecha_recibido.replace(tzinfo=None), 
            factura.emisor,
            factura.cedula,
            factura.moneda,
            factura.total
        ])

    # Configurar la respuesta
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="reporte_facturas_infinytsolutions.xlsx"'
    
    wb.save(response)
    return response

def guardar_configuracion(request):
    config, _ = ConfiguracionSistema.objects.get_or_create(id=1)
    if request.method == 'POST':
        config.meses_historial = request.POST.get('meses')
        config.save()
        return redirect('/') # O tu vista principal
    return render(request, 'configurar.html', {'config': config})