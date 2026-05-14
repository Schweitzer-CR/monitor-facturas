import imaplib
import email
import xml.etree.ElementTree as ET
import json
import datetime
from .models import Factura

def safe_get(node, path, namespaces, default="N/A"):
    """
    Busca un nodo y extrae su texto de forma segura.
    Si el nodo no existe o no tiene texto, devuelve el valor por defecto.
    """
    found = node.find(path, namespaces)
    if found is not None and found.text:
        return found.text.strip()
    return default

def revisar_gmail(user, password):
    """
    Conecta a Gmail, busca facturas de Hacienda CR y guarda la información detallada.
    """
    try:
        # 1. Conexión al servidor IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, password)
        mail.select("INBOX")
        
        # 2. Configuración de fecha para la búsqueda (Formato: 13-May-2026)
        # Buscamos desde ayer para no saturar el servidor con miles de correos antiguos
        ayer = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")
        
        # Criterio de búsqueda estándar compatible con Gmail
        criterio = f'(SINCE {ayer} BODY "xml")'
        status, mensajes = mail.search(None, criterio)
        
        if status != 'OK':
            print(f"⚠️ Error en la búsqueda de Gmail: {status}")
            return

        ids = mensajes[0].split()
        
        # Procesamos los últimos 10 correos encontrados
        for mail_id in ids[-10:]:
            str_id = mail_id.decode()
            
            # Evitar duplicados: Si ya existe en BD, saltar
            if Factura.objects.filter(mensaje_id=str_id).exists():
                continue

            # 3. Descarga y parseo del correo
            res, data = mail.fetch(mail_id, "(RFC822)")
            if res != 'OK': continue
            
            msg = email.message_from_bytes(data[0][1])

            # 4. Recorrer partes del correo buscando el XML
            for part in msg.walk():
                filename = part.get_filename()
                
                if filename and filename.lower().endswith('.xml'):
                    xml_content = part.get_payload(decode=True)
                    
                    try:
                        # 5. Parseo del XML con manejo dinámico de Namespaces
                        root = ET.fromstring(xml_content)
                        ns_url = root.tag.split('}')[0].strip('{')
                        ns = {'ns': ns_url}

                        # --- Extracción Segura de Datos Principales ---
                        emisor = safe_get(root, ".//ns:Emisor/ns:Nombre", ns, "Emisor Desconocido")
                        cedula = safe_get(root, ".//ns:Emisor/ns:Identificacion/ns:Numero", ns, "0-0000-0000")
                        total_raw = safe_get(root, ".//ns:ResumenFactura/ns:TotalComprobante", ns, "0")
                        moneda = safe_get(root, ".//ns:ResumenFactura/ns:CodigoTipoMoneda/ns:CodigoMoneda", ns, "CRC")
                        
                        # --- Extracción de Líneas de Detalle (Productos) ---
                        lineas_detalle = []
                        for linea in root.findall(".//ns:LineaDetalle", ns):
                            item = {
                                'cantidad': safe_get(linea, ".//ns:Cantidad", ns, "1"),
                                'detalle': safe_get(linea, ".//ns:Detalle", ns, "Sin descripción"),
                                'precio': safe_get(linea, ".//ns:PrecioUnitario", ns, "0"),
                                'monto': safe_get(linea, ".//ns:MontoTotal", ns, "0"),
                            }
                            lineas_detalle.append(item)

                        # 6. Guardar en Base de Datos
                        # Convertimos total a float, si falla ponemos 0.0
                        try:
                            total_final = float(total_raw)
                        except ValueError:
                            total_final = 0.0

                        Factura.objects.create(
                            emisor=emisor,
                            cedula=cedula,
                            total=total_final,
                            moneda=moneda,
                            mensaje_id=str_id,
                            detalles_json=json.dumps(lineas_detalle)
                        )
                        print(f"✅ Factura guardada: {emisor} por {total_final} {moneda}")

                    except Exception as xml_err:
                        # Si un XML falla, imprimimos el error y seguimos con el siguiente correo
                        print(f"⚠️ Saltando XML corrupto o no compatible: {xml_err}")
                        continue
        
        mail.logout()

    except imaplib.IMAP4.error as auth_err:
        print(f"❌ Error de autenticación: {auth_err}. Revisa tus credenciales.")
    except Exception as e:
        print(f"❌ Error inesperado en utils.py: {e}")