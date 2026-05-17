import imaplib
import email
import xml.etree.ElementTree as ET
import json
import datetime
from django.core.mail import EmailMessage, get_connection # Importación para SMTP dinámico
from .models import Factura, ConfiguracionSistema 

def safe_get(node, path, namespaces, default="N/A"):
    found = node.find(path, namespaces)
    if found is not None and found.text:
        return found.text.strip()
    return default

def enviar_factura_nueva(emisor, xml_data, xml_name, msg_original, auth_user, auth_password):
    """
    Crea un correo nuevo utilizando de forma dinámica las credenciales 
    del usuario que inició sesión, sin guardar nada fijo en settings.py.
    """
    subject = f"🚀 Nueva Factura: {emisor}"
    body = f"Se ha detectado una nueva factura de {emisor} en el monitor.\nSe adjuntan los archivos encontrados."
    destino = "moracastrojordan@gmail.com"
    
    # 1. Establecemos la conexión SMTP efímera con los datos pasados en tiempo de ejecución
    conexion_dinamica = get_connection(
        username=auth_user,
        password=auth_password,
        fail_silently=False
    )
    
    # 2. Asignamos la conexión explícita al objeto EmailMessage
    email_send = EmailMessage(
        subject=subject, 
        body=body, 
        to=[destino],
        connection=conexion_dinamica
    )
    
    # Adjuntamos el XML que está en memoria
    email_send.attach(xml_name, xml_data, 'text/xml')
    
    # Buscamos el PDF dentro de las partes del mensaje original para adjuntarlo también
    for part in msg_original.walk():
        filename = part.get_filename()
        if filename and filename.lower().endswith('.pdf'):
            pdf_data = part.get_payload(decode=True)
            email_send.attach(filename, pdf_data, 'application/pdf')
    
    # 3. Enviamos el correo a través del puente dinámico seguro
    email_send.send()

def revisar_gmail(user, password):
    try:
        # 1. Conexión segura al servidor IMAP utilizando el login dinámico
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, password)
        mail.select("INBOX")
        
        config, _ = ConfiguracionSistema.objects.get_or_create(id=1)
        meses = config.meses_historial
        
        # Mantenemos el criterio amplio para escaneo de comprobantes de cualquier emisor costarricense
        fecha_limite = datetime.date.today() - datetime.timedelta(days=meses * 30)
        fecha_busqueda = fecha_limite.strftime("%d-%b-%Y")
        
        criterio = f'(SINCE {fecha_busqueda} BODY "xml")'
        status, mensajes = mail.search(None, criterio)
        
        if status != 'OK': return

        # Obtenemos los IDs y les aplicamos reverso para digerir primero lo más reciente
        ids = mensajes[0].split()
        ids.reverse() 

        procesados_en_lote = 0
        LIMITE_BATCH = 25 # Mantiene las cargas fluidas sin colapsar el refresh de la página web

        for mail_id in ids:
            if procesados_en_lote >= LIMITE_BATCH:
                print(f"⏸️ Lote de {LIMITE_BATCH} completado. Sincronizando el resto en la próxima vuelta...")
                break

            str_id = mail_id.decode()
            
            # Si ya se encuentra registrado en el sistema local, saltamos de inmediato
            if Factura.objects.filter(mensaje_id=str_id).exists():
                continue

            res, data = mail.fetch(mail_id, "(RFC822)")
            if res != 'OK': continue
            
            msg = email.message_from_bytes(data[0][1])
            
            xml_para_enviar = None
            nombre_xml = ""
            factura_creada = False
            emisor_nombre = ""

            for part in msg.walk():
                filename = part.get_filename()
                
                # Identificamos el archivo de estructura XML
                if filename and filename.lower().endswith('.xml'):
                    xml_content = part.get_payload(decode=True)
                    
                    try:
                        root = ET.fromstring(xml_content)
                        ns_url = root.tag.split('}')[0].strip('{')
                        ns = {'ns': ns_url}

                        # Confirmamos que posea la estructura de un comprobante electrónico nacional
                        if root.find(".//ns:Emisor", ns) is not None:
                            emisor = safe_get(root, ".//ns:Emisor/ns:Nombre", ns, "Emisor Desconocido")
                            cedula = safe_get(root, ".//ns:Emisor/ns:Identificacion/ns:Numero", ns, "0-0000-0000")
                            total_raw = safe_get(root, ".//ns:ResumenFactura/ns:TotalComprobante", ns, "0")
                            moneda = safe_get(root, ".//ns:ResumenFactura/ns:CodigoTipoMoneda/ns:CodigoMoneda", ns, "CRC")
                            
                            lineas_detalle = []
                            for linea in root.findall(".//ns:LineaDetalle", ns):
                                item = {
                                    'cantidad': safe_get(linea, ".//ns:Cantidad", ns, "1"),
                                    'detalle': safe_get(linea, ".//ns:Detalle", ns, "Sin descripción"),
                                    'precio': safe_get(linea, ".//ns:PrecioUnitario", ns, "0"),
                                    'monto': safe_get(linea, ".//ns:MontoTotal", ns, "0"),
                                }
                                lineas_detalle.append(item)

                            try:
                                total_final = float(total_raw)
                            except ValueError:
                                total_final = 0.0

                            # Guardamos la entidad en persistencia
                            Factura.objects.create(
                                emisor=emisor,
                                cedula=cedula,
                                total=total_final,
                                moneda=moneda,
                                mensaje_id=str_id,
                                detalles_json=json.dumps(lineas_detalle)
                            )
                            
                            xml_para_enviar = xml_content
                            nombre_xml = filename
                            emisor_nombre = emisor
                            factura_creada = True
                            procesados_en_lote += 1
                        
                    except Exception as e:
                        print(f"⚠️ Error parseando XML: {e}")
                        continue
            
            # Disparamos el reenvío inmediato solo si se detectó como documento nuevo y válido
            if factura_creada:
                try:
                    # Inyectamos de forma explícita el usuario y token/clave de aplicación para la conexión SMTP
                    enviar_factura_nueva(emisor_nombre, xml_para_enviar, nombre_xml, msg, user, password)
                    print(f"📧 Reenviada de forma segura: {emisor_nombre} a moracastrojordan@gmail.com")
                except Exception as e:
                    print(f"❌ Error al enviar correo: {e}")
        
        mail.logout()

    except Exception as e:
        print(f"❌ Error general en monitoreo: {e}")