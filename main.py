import flet as ft
from pymongo import MongoClient
import sqlite3
import os
from datetime import datetime, timedelta
import unicodedata
import re
import threading
import smtplib
import random
from email.message import EmailMessage

MONGO_URI = "mongodb+srv://admin_biblioteca:Lopezmateo0710@biblioteca.cz999dn.mongodb.net/?retryWrites=true&w=majority&appName=biblioteca"
CORREO_REMITENTE = "avisos.biblioteca.adolfolm@gmail.com"
PASSWORD_APP = "idyhkqahuxnzcosd"
CARPETA_ANDROID = os.environ.get("FLET_APP_STORAGE_DATA", ".")
RUTA_DB = os.path.join(CARPETA_ANDROID, "movil_cache.db")
def inicializar_cache():
    conexion = sqlite3.connect(RUTA_DB)
    cursor = conexion.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS sync_usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre_completo TEXT, edad TEXT, telefono TEXT, correo TEXT,
                        fecha_expedicion TEXT, fecha_vencimiento TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS sync_prestamos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre_usuario TEXT, nombre_libro TEXT,
                        fecha_prestamo TEXT, fecha_entrega TEXT)''')
    conexion.commit()
    conexion.close()

inicializar_cache()
def enviar_correo_silencioso(correo, nombre, libros, fecha_limite):
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=5)
        server.login(CORREO_REMITENTE, PASSWORD_APP)
        msg = EmailMessage()
        msg['Subject'] = "Confirmación de Préstamo "
        msg['From'] = f"Biblioteca Centro Recreativo <{CORREO_REMITENTE}>"
        msg['To'] = correo
        libros_str = "\n- ".join(libros)
        msg.set_content(f"Hola {nombre},\n\nHas solicitado el préstamo de:\n\n- {libros_str}\n\n Devolución límite: {fecha_limite} (Días hábiles).")
        server.send_message(msg)
        server.quit()
    except Exception:
        pass

def main(page: ft.Page):
    page.title = "BiblioApp Móvil"
    page.window_width = 400
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    try:
        CLIENTE_MONGO = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2500, tls=True, tlsAllowInvalidCertificates=True)
        DB_NUBE = CLIENTE_MONGO['biblioteca_centro']
    except Exception:
        pass

    banner_alerta = ft.Text("", size=16, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    
    def mostrar_alerta(mensaje, color):
        banner_alerta.value = mensaje
        banner_alerta.color = color
        page.update()

    nombre_u = ft.TextField(label="Nombre Completo", prefix_icon=ft.Icons.PERSON, border_radius=10)
    edad_u = ft.TextField(label="Edad", keyboard_type=ft.KeyboardType.NUMBER, prefix_icon=ft.Icons.CALENDAR_TODAY, border_radius=10)
    tel_u = ft.TextField(label="Teléfono Móvil", keyboard_type=ft.KeyboardType.PHONE, prefix_icon=ft.Icons.PHONE, border_radius=10)
    correo_u = ft.TextField(label="Correo Electrónico", keyboard_type=ft.KeyboardType.EMAIL, prefix_icon=ft.Icons.EMAIL, border_radius=10)
    check_rapido = ft.Checkbox(label="Modo Rápido (Omitir correo)", value=False)

    def guardar_usuario(e):
        try:
            mostrar_alerta("", ft.Colors.TRANSPARENT)
            
            if not nombre_u.value or not tel_u.value:
                mostrar_alerta("Nombre y teléfono son obligatorios.", ft.Colors.RED_400)
                return

            if len(tel_u.value.strip()) != 10 or not tel_u.value.strip().isdigit():
                mostrar_alerta(" El teléfono debe tener 10 números exactos.", ft.Colors.RED_400)
                return
                
            btn_gu.disabled = True
            btn_gu.text = "Procesando..."
            page.update()
            
            fhoy = datetime.now()
            fvenc = fhoy + timedelta(days=730)
            
            nuevo_usr = {
                "nombre_completo": nombre_u.value.strip().title(),
                "edad": edad_u.value.strip(),
                "domicilio": "Pendiente desde app", "cp": "S/R",
                "telefono": tel_u.value.strip(), "telefono2": "S/R",
                "ocupacion": "S/R", "escuela_trabajo": "S/R",
                "fecha_expedicion": fhoy.strftime("%d/%m/%Y"),
                "fecha_vencimiento": fvenc.strftime("%d/%m/%Y"),
                "correo": correo_u.value.strip().lower()
            }
            
            try:
                CLIENTE_MONGO.admin.command('ping')
                
                if check_rapido.value == True or not correo_u.value:
                    DB_NUBE['usuarios'].insert_one(nuevo_usr)
                    mostrar_alerta(" Usuario guardado en la nube", ft.Colors.GREEN_400)
                    nombre_u.value = ""; edad_u.value = ""; tel_u.value = ""; correo_u.value = ""
                else:
                    codigo_generado = str(random.randint(100000, 999999))
                    btn_gu.text = "Enviando código..."
                    page.update()
                    
                    try:
                        msg = EmailMessage()
                        msg['Subject'] = "Código de verificación - Biblioteca"
                        msg['From'] = f"Biblioteca Centro Recreativo <{CORREO_REMITENTE}>"
                        msg['To'] = correo_u.value.strip().lower()
                        msg.set_content(f"Hola {nombre_u.value.strip().title()},\n\nTu código de verificación es: {codigo_generado}")

                        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=4)
                        server.login(CORREO_REMITENTE, PASSWORD_APP)
                        server.send_message(msg)
                        server.quit()
                        
                        txt_codigo = ft.TextField(label="Código de 6 dígitos", keyboard_type=ft.KeyboardType.NUMBER)
                        
                        def verificar(e):
                            if txt_codigo.value == codigo_generado:
                                dlg.open = False
                                DB_NUBE['usuarios'].insert_one(nuevo_usr)
                                mostrar_alerta(" Código correcto Guardado en la nube.", ft.Colors.GREEN_400)
                                nombre_u.value = ""; edad_u.value = ""; tel_u.value = ""; correo_u.value = ""
                            else:
                                mostrar_alerta(" Código incorrecto.", ft.Colors.RED_400)
                                
                            btn_gu.text = "Guardar Usuario"
                            btn_gu.disabled = False
                            page.update()

                        def cancelar(e):
                            dlg.open = False
                            btn_gu.text = "Guardar Usuario"
                            btn_gu.disabled = False
                            page.update()

                        dlg = ft.AlertDialog(
                            title=ft.Text("Verificación de Correo"),
                            content=ft.Column([ft.Text(f"Se envió a {correo_u.value.lower()}"), txt_codigo], tight=True),
                            actions=[
                                ft.TextButton("Verificar", on_click=verificar),
                                ft.TextButton("Cancelar", on_click=cancelar)
                            ]
                        )
                        page.overlay.append(dlg)
                        dlg.open = True
                        page.update()
                        return 
                        
                    except Exception:
                        mostrar_alerta(" Falló el correo. Usa Modo Rápido.", ft.Colors.RED_400)

            except Exception:
                con = sqlite3.connect(RUTA_DB)
                con.execute("INSERT INTO sync_usuarios (nombre_completo, edad, telefono, correo, fecha_expedicion, fecha_vencimiento) VALUES (?,?,?,?,?,?)", 
                            (nuevo_usr["nombre_completo"], nuevo_usr["edad"], nuevo_usr["telefono"], nuevo_usr["correo"], nuevo_usr["fecha_expedicion"], nuevo_usr["fecha_vencimiento"]))
                con.commit()
                con.close()
                
                mostrar_alerta(" Sin red. Usuario guardado en el teléfono.", ft.Colors.ORANGE_400)
                nombre_u.value = ""; edad_u.value = ""; tel_u.value = ""; correo_u.value = ""
        
        except Exception as error_critico:
            mostrar_alerta(f" Error interno: {error_critico}", ft.Colors.RED_400)
            
        finally:
            btn_gu.disabled = False
            btn_gu.text = "Guardar Usuario"
            page.update()

    btn_gu = ft.ElevatedButton("Guardar Usuario", on_click=guardar_usuario, width=350, height=50, style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE))

    nombre_p = ft.TextField(label="Nombre del Usuario", prefix_icon=ft.Icons.PERSON_SEARCH, border_radius=10)
    libro_p = ft.TextField(label="Libros (separados por coma)", prefix_icon=ft.Icons.MENU_BOOK, border_radius=10)

    def guardar_prestamo(e):
        try:
            mostrar_alerta("", ft.Colors.TRANSPARENT)
            if not nombre_p.value or not libro_p.value:
                mostrar_alerta("Llena todos los campos.", ft.Colors.RED_400)
                return
                
            btn_gp.disabled = True
            btn_gp.text = "Guardando..."
            page.update()

            fhoy = datetime.now()
            fent = fhoy
            dias = 5
            while dias > 0:
                fent += timedelta(days=1)
                if fent.weekday() < 5:
                    dias -= 1
            
            s_hoy = fhoy.strftime("%d/%m/%Y")
            s_ent = fent.strftime("%d/%m/%Y")
            lista_libros = [l.strip().title() for l in libro_p.value.split(",") if l.strip()]

            try:
                CLIENTE_MONGO.admin.command('ping')
                col_u = DB_NUBE['usuarios']
                col_p = DB_NUBE['prestamos']

                buscado = nombre_p.value.strip()
                encontrado = None
                correo_usr = None
                
                patron = re.escape(buscado)
                usr = col_u.find_one({"nombre_completo": {"$regex": patron, "$options": "i"}})
                
                if usr:
                    encontrado = usr["nombre_completo"]
                    correo_usr = usr.get("correo")
                
                if not encontrado:
                    mostrar_alerta(" Usuario no encontrado.", ft.Colors.RED_400)
                    btn_gp.text = "Registrar Préstamo"
                    btn_gp.disabled = False
                    page.update()
                    return

                for lib in lista_libros:
                    col_p.insert_one({"nombre_usuario": encontrado, "nombre_libro": lib, "fecha_prestamo": s_hoy, "fecha_entrega": s_ent, "estado": "Pendiente"})
                
                if correo_usr:
                    threading.Thread(target=enviar_correo_silencioso, args=(correo_usr, encontrado, lista_libros, s_ent)).start()

                mostrar_alerta(f" ¡Préstamo activo! Devolución: {s_ent}", ft.Colors.GREEN_400)
                nombre_p.value = ""; libro_p.value = ""
            
            except Exception:
                con = sqlite3.connect(RUTA_DB)
                for lib in lista_libros:
                    con.execute("INSERT INTO sync_prestamos (nombre_usuario, nombre_libro, fecha_prestamo, fecha_entrega) VALUES (?,?,?,?)", 
                                (nombre_p.value.strip().title(), lib, s_hoy, s_ent))
                con.commit()
                con.close()
                
                mostrar_alerta(f" Sin red. Préstamo guardado local.", ft.Colors.ORANGE_400)
                nombre_p.value = ""; libro_p.value = ""

        except Exception as error_critico:
            mostrar_alerta(f" Error interno: {error_critico}", ft.Colors.RED_400)
            
        finally:
            btn_gp.disabled = False
            btn_gp.text = "Registrar Préstamo"
            page.update()

    btn_gp = ft.ElevatedButton("Registrar Préstamo", on_click=guardar_prestamo, width=350, height=50, style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE))

    vista_usuarios = ft.Column([
        ft.Text("Nuevo Registro", size=24, weight=ft.FontWeight.BOLD),
        nombre_u, edad_u, tel_u, correo_u, check_rapido,
        ft.Container(height=10), btn_gu
    ], spacing=15, visible=True)

    vista_prestamos = ft.Column([
        ft.Text("Salida de Libros", size=24, weight=ft.FontWeight.BOLD),
        nombre_p, libro_p,
        ft.Container(height=10), btn_gp
    ], spacing=15, visible=False)

    def mostrar_usuarios(e):
        mostrar_alerta("", ft.Colors.TRANSPARENT)
        vista_usuarios.visible = True
        vista_prestamos.visible = False
        btn_nav_u.style.color = ft.Colors.BLUE_400
        btn_nav_p.style.color = ft.Colors.GREY_500
        page.update()

    def mostrar_prestamos(e):
        mostrar_alerta("", ft.Colors.TRANSPARENT)
        vista_usuarios.visible = False
        vista_prestamos.visible = True
        btn_nav_u.style.color = ft.Colors.GREY_500
        btn_nav_p.style.color = ft.Colors.BLUE_400
        page.update()

    btn_nav_u = ft.TextButton(" Usuarios", on_click=mostrar_usuarios, style=ft.ButtonStyle(color=ft.Colors.BLUE_400))
    btn_nav_p = ft.TextButton(" Préstamos", on_click=mostrar_prestamos, style=ft.ButtonStyle(color=ft.Colors.GREY_500))
    barra_navegacion = ft.Row([btn_nav_u, btn_nav_p], alignment=ft.MainAxisAlignment.CENTER)

    def sincronizar(e):
        try:
            btn_sync.disabled = True
            mostrar_alerta("Sincronizando...", ft.Colors.BLUE_400)
            
            CLIENTE_MONGO.admin.command('ping')
            
            con = sqlite3.connect(RUTA_DB)
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            
            cur.execute("SELECT * FROM sync_usuarios")
            usuarios_offline = cur.fetchall()
            for u in usuarios_offline:
                d = dict(u)
                d.pop('id')
                d.update({"domicilio": "Pendiente", "cp": "S/R", "telefono2": "S/R", "ocupacion": "S/R", "escuela_trabajo": "S/R"})
                DB_NUBE['usuarios'].insert_one(d)
            cur.execute("DELETE FROM sync_usuarios")
            
            cur.execute("SELECT * FROM sync_prestamos")
            prestamos_offline = cur.fetchall()
            for p in prestamos_offline:
                d = dict(p)
                d.pop('id')
                d.update({"estado": "Pendiente"})
                DB_NUBE['prestamos'].insert_one(d)
            cur.execute("DELETE FROM sync_prestamos")
            
            con.commit()
            con.close()
            
            total = len(usuarios_offline) + len(prestamos_offline)
            if total > 0:
                mostrar_alerta(f" ¡{total} registros subidos con éxito!", ft.Colors.BLUE_400)
            else:
                mostrar_alerta(" Todo está sincronizado.", ft.Colors.BLUE_400)
                
        except Exception:
            mostrar_alerta("Aún no hay red para sincronizar.", ft.Colors.RED_400)
        finally:
            btn_sync.disabled = False
            page.update()

    btn_sync = ft.IconButton(icon=ft.Icons.SYNC, icon_color=ft.Colors.WHITE, on_click=sincronizar, tooltip="Sincronizar Datos")
    header = ft.Row([ft.Text("BiblioApp", size=22, weight=ft.FontWeight.BOLD), btn_sync], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    page.add(header, banner_alerta, barra_navegacion, ft.Divider(height=1, color=ft.Colors.GREY_800), vista_usuarios, vista_prestamos)

ft.app(target=main)
