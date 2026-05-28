import imaplib
import email
import xml.etree.ElementTree as ET
import json
import datetime
from django.core.mail import EmailMessage, get_connection
from .models import Factura, ConfiguracionSistema, CuentaCorreoCliente 

def safe_get(node, path, namespaces, default="N/A"):
    found = node.find(path, namespaces)
    if found is not None and found.text:
        return found.text.strip()
    return default

def obtener_config_proveedor(correo):
    correo_lower = correo.lower()
    if "@gmail.com" in correo_lower:
        return {"imap_server": "imap.gmail.com", "smtp_server": "smtp.gmail.com"}
    else:
        return {"imap_server": "outlook.office365.com", "smtp_server": "smtp.office.office365.com"}

def enviar_factura_nueva(emisor, xml_data, xml_name, msg_original, auth_user, auth_password, destino):
    subject = f"Nueva Factura: {emisor}"
    body = f"Se ha detectado una nueva factura de {emisor} en el monitor.\nSe adjuntan los archivos encontrados."
    
    config_prov = obtener_config_proveedor(auth_user)
    
    conexion_dinamica = get_connection(
        host=config_prov["smtp_server"],
        port=587,
        username=auth_user,
        password=auth_password,
        use_tls=True,
        fail_silently=False
    )
    
    email_send = EmailMessage(subject=subject, body=body, to=[destino], connection=conexion_dinamica)
    email_send.attach(xml_name, xml_data, 'text/xml')
    
    for part in msg_original.walk():
        filename = part.get_filename()
        if filename and filename.lower().endswith('.pdf'):
            email_send.attach(filename, part.get_payload(decode=True), 'application/pdf')
    
    email_send.send()

def procesar_correos_usuario(usuario_web):
    try:
        config, _ = ConfiguracionSistema.objects.get_or_create(usuario_web=usuario_web)
        fecha_limite = datetime.date.today() - datetime.timedelta(days=config.meses_historial * 30)
        criterio = f'(SINCE {fecha_limite.strftime("%d-%b-%Y")} BODY "xml")'

        for cuenta in CuentaCorreoCliente.objects.filter(usuario_web=usuario_web):
            try:
                config_prov = obtener_config_proveedor(cuenta.correo_origen)
                mail = imaplib.IMAP4_SSL(config_prov["imap_server"])
                mail.login(cuenta.correo_origen, cuenta.password_aplicacion)
                mail.select("INBOX")
                
                _, mensajes = mail.search(None, criterio)
                ids = mensajes[0].split()
                ids.reverse() 

                procesados_en_lote = 0
                for mail_id in ids:
                    if procesados_en_lote >= 25: break
                    
                    str_id = mail_id.decode()
                    if Factura.objects.filter(mensaje_id=str_id).exists(): continue

                    _, data = mail.fetch(mail_id, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    
                    factura_creada = False
                    for part in msg.walk():
                        filename = part.get_filename()
                        if filename and filename.lower().endswith('.xml'):
                            xml_content = part.get_payload(decode=True)
                            
                            # --- FILTRO DE SEGURIDAD ---
                            # Si el archivo no empieza con '<', es basura o error de codificación
                            if not xml_content.strip().startswith(b'<'):
                                continue
                            
                            try:
                                root = ET.fromstring(xml_content)
                                ns_url = root.tag.split('}')[0].strip('{')
                                ns = {'ns': ns_url}

                                if root.find(".//ns:Emisor", ns) is not None:
                                    emisor = safe_get(root, ".//ns:Emisor/ns:Nombre", ns, "Emisor Desconocido")
                                    
                                    Factura.objects.create(
                                        usuario_web=usuario_web,
                                        cuenta_cliente=cuenta,
                                        emisor=emisor,
                                        cedula=safe_get(root, ".//ns:Emisor/ns:Identificacion/ns:Numero", ns, "0"),
                                        total=float(safe_get(root, ".//ns:ResumenFactura/ns:TotalComprobante", ns, "0")),
                                        moneda=safe_get(root, ".//ns:ResumenFactura/ns:CodigoTipoMoneda/ns:CodigoMoneda", ns, "CRC"),
                                        mensaje_id=str_id,
                                        detalles_json=json.dumps([{'detalle': safe_get(l, ".//ns:Detalle", ns)} for l in root.findall(".//ns:LineaDetalle", ns)])
                                    )
                                    enviar_factura_nueva(emisor, xml_content, filename, msg, cuenta.correo_origen, cuenta.password_aplicacion, config.correo_destino)
                                    factura_creada = True
                                    procesados_en_lote += 1
                            except Exception as e:
                                print(f"⚠️ Error procesando XML: {e}")
                
                mail.logout()
            except Exception as e:
                print(f"❌ Error en cuenta {cuenta.correo_origen}: {e}")
                
    except Exception as e:
        print(f"❌ Error general: {e}")