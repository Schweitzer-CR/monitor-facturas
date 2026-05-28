from django.shortcuts import render, redirect, get_object_or_404
import json
from django.utils import timezone
import openpyxl
from django.http import HttpResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from .models import Factura, ConfiguracionSistema, CuentaCorreoCliente
from .utils import procesar_correos_usuario
from django.utils.dateparse import parse_date

HORA_INICIO = timezone.now()

def login_view(request):
    # Si el usuario ya está autenticado, lo enviamos al monitor
    if request.user.is_authenticated:
        return redirect('monitor')

    if request.method == 'POST':
        # Buscamos el campo 'username' que viene del HTML
        usuario_web = request.POST.get('username')
        clave_web = request.POST.get('password')
        
        # Autenticamos usando el sistema interno de Django
        user = authenticate(request, username=usuario_web, password=clave_web)
        
        if user is not None:
            auth_login(request, user)
            return redirect('monitor')
        else:
            # Enviamos el error para que el HTML lo muestre
            return render(request, 'facturas/login.html', {
                'error': 'Usuario o contraseña web incorrectos'
            })
            
    return render(request, 'facturas/login.html')

@login_required(login_url='login')
def monitor_view(request):
    # Capturamos el filtro de cliente si existe
    cliente_id = request.GET.get('cliente_id')
    
    # 1. Lógica para actualizaciones HTMX
    if request.headers.get('HX-Request'):
        procesar_correos_usuario(request.user)
        
        # Filtramos las facturas del usuario
        facturas = Factura.objects.filter(usuario_web=request.user)
        
        # Si se seleccionó un cliente específico, filtramos por él
        if cliente_id and cliente_id != "todos":
            facturas = facturas.filter(cuenta_cliente_id=cliente_id)
            
        facturas = facturas.order_by('-fecha_recibido')
        return render(request, 'facturas/lista_facturas.html', {'facturas': facturas})
    
    # 2. Lógica para carga inicial de la página
    config, _ = ConfiguracionSistema.objects.get_or_create(usuario_web=request.user)
    cuentas = CuentaCorreoCliente.objects.filter(usuario_web=request.user)
    
    # Filtramos para la carga inicial
    facturas = Factura.objects.filter(usuario_web=request.user)
    if cliente_id and cliente_id != "todos":
        facturas = facturas.filter(cuenta_cliente_id=cliente_id)
    
    facturas = facturas.order_by('-fecha_recibido')
    
    return render(request, 'facturas/monitor.html', {
        'facturas': facturas,
        'config': config,
        'cuentas': cuentas,
        'cliente_seleccionado': cliente_id # Útil para mantener el select marcado
    })


def logout_view(request):
    auth_logout(request)
    return redirect('login')


@login_required(login_url='login')
def factura_detalle(request, pk):
    # Por seguridad, nos aseguramos de que esta factura le pertenece al usuario actual
    factura = get_object_or_404(Factura, pk=pk, usuario_web=request.user)
    
    # Convertimos el texto JSON de la base de datos a una lista de Python
    productos = json.loads(factura.detalles_json)
    
    return render(request, 'facturas/detalle.html', {
        'factura': factura,
        'productos': productos
    })


@login_required(login_url='login')
def exportar_facturas_excel(request):
    # 1. Capturar las fechas del formulario (vienen por método GET)
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    
    # Convertir los strings de la interfaz a objetos de tipo fecha de Python
    fecha_inicio = parse_date(fecha_inicio_str) if fecha_inicio_str else None
    fecha_fin = parse_date(fecha_fin_str) if fecha_fin_str else None

    # Crear un nuevo libro de Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte de Facturas"

    # Definir los encabezados del Excel
    headers = ['Fecha Recibido', 'Emisor', 'Cédula', 'Moneda', 'Total']
    ws.append(headers)

    # 2. Filtrar base: solo las facturas del usuario web actual
    facturas = Factura.objects.filter(usuario_web=request.user)

    # 3. Aplicar los filtros de rango de fechas si el usuario los seleccionó
    if fecha_inicio:
        facturas = facturas.filter(fecha_recibido__date__gte=fecha_inicio)
    if fecha_fin:
        facturas = facturas.filter(fecha_recibido__date__lte=fecha_fin)

    # Ordenar los resultados finales por fecha de recibido más reciente
    facturas = facturas.order_by('-fecha_recibido')

    # Agregar los datos al archivo de Excel
    for factura in facturas:
        # Asegurar que si la fecha es nula por alguna razón, no rompa el bucle
        fecha_limpia = factura.fecha_recibido.replace(tzinfo=None) if factura.fecha_recibido else ''
        
        ws.append([
            fecha_limpia, 
            factura.emisor,
            factura.cedula,
            factura.moneda,
            factura.total
        ])

    # Configurar la respuesta de descarga dinámica
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    
    # Nombre del archivo dinámico indicando el periodo descargado
    if fecha_inicio_str and fecha_fin_str:
        filename = f'reporte_facturas_{fecha_inicio_str}_al_{fecha_fin_str}.xlsx'
    else:
        filename = 'reporte_facturas_completo.xlsx'
        
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb.save(response)
    return response


@login_required(login_url='login')
def guardar_configuracion(request):
    # Obtenemos la configuración EXCLUSIVA de este usuario
    config, _ = ConfiguracionSistema.objects.get_or_create(usuario_web=request.user)
    
    if request.method == 'POST':
        meses = request.POST.get('meses')
        nuevo_correo = request.POST.get('correo_destino')
        
        if meses:
            config.meses_historial = int(meses)
        if nuevo_correo:
            config.correo_destino = nuevo_correo.strip()
            
        config.save()
        
    return redirect('/') 


@login_required(login_url='login')
def guardar_cliente(request):

    if request.method == 'POST':
        nombre = request.POST.get('nombre_cliente')
        correo = request.POST.get('correo_origen')
        clave = request.POST.get('password_aplicacion')
        
        if nombre and correo and clave:
            CuentaCorreoCliente.objects.create(
                usuario_web=request.user,
                nombre_cliente=nombre.strip(),
                correo_origen=correo.strip(),
                password_aplicacion=clave.strip()
            )
            
    return redirect('/')

@login_required(login_url='login')
def eliminar_cliente(request, pk):
    cliente = get_object_or_404(CuentaCorreoCliente, pk=pk, usuario_web=request.user)
    if request.method == 'POST':
        cliente.delete()
    return redirect('monitor') 