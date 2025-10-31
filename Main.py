import Controller_Error
import Setting as ST
import time
from datetime import datetime
import SerialCOM as SC_SIN_SIM
import serial
import threading
import queue
import Consultas_SIM as CS
import os
import sys
import Alertas as AT
import LogCreator as LG
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable
from CierreAutomatico import CerrarVentanaAutomatica
from VentanaTopMost import VentanaTopMost, VentanaTkinterTopMost
import win32con
import win32gui

root = tk.Tk()
root.withdraw()

# Hacer que todas las ventanas tkinter (popups) sean topmost
VentanaTkinterTopMost.set_topmost(root)

avisos = AT.PopUpAvisos(titulo_app="Abril SIM")

# Cola thread-safe para mostrar pop-ups desde el hilo principal
popup_queue = queue.Queue()

def procesar_popups():
    """Procesa pop-ups pendientes en la cola desde el hilo principal"""
    try:
        while not popup_queue.empty():
            popup_data = popup_queue.get_nowait()
            tipo = popup_data.get('tipo')
            mensaje = popup_data.get('mensaje')
            titulo = popup_data.get('titulo', 'Notificación')
            
            if tipo == 'fail':
                avisos.fail(mensaje, titulo=titulo)
            elif tipo == 'pass':
                avisos.pass_temporal(mensaje, titulo=titulo)
    except queue.Empty:
        pass
    except Exception as e:
        print(f"Error procesando popup: {e}")

def mostrar_popup_fail(mensaje, titulo="Error"):
    """Encola un popup de error para mostrarlo en el hilo principal"""
    popup_queue.put({'tipo': 'fail', 'mensaje': mensaje, 'titulo': titulo})

def mostrar_popup_timeout(mensaje, titulo="Timeout"):
    """Encola un popup de timeout para mostrarlo en el hilo principal"""
    popup_queue.put({'tipo': 'timeout', 'mensaje': mensaje, 'titulo': titulo})

    """Encola un popup de timeout para mostrarlo en el hilo principal"""
    popup_queue.put({'tipo': 'timeout', 'mensaje': mensaje, 'titulo': titulo})

def mostrar_popup_pass(mensaje, titulo="Éxito"):
    """Encola un popup de éxito para mostrarlo en el hilo principal"""
    popup_queue.put({'tipo': 'pass', 'mensaje': mensaje, 'titulo': titulo})

def atraer_al_frente(ventana,HWND:int) -> bool:
    try:
            if ventana.winfo_exists():
                    # HWND_TOPMOST = -1 significa "siempre al frente"
                    win32gui.SetWindowPos(
                        HWND,
                        win32con.HWND_TOPMOST,  # -1
                        0, 0, 0, 0,
                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
                    )
            return True
    except Exception as e:
            return False

configuracion, modo_desarrollador = ST.Setting.obtener_puertos_comunicaciones()
configuracion_MES = ST.Setting.obtener_parametros_MES()
valores_definidos_taxis = ST.Setting.obtener_Comandos_PLC()
Activador_MES = configuracion_MES["habilitar_mes"]
directorio_salida = configuracion_MES["directorio_logs"]
puerto_escaner, baudrate_escaner = ST.Setting.obtener_datos_escaner()

print(puerto_escaner, baudrate_escaner)
# Inicializar el gestor de logs
logger = LG.LogManager(directorio_salida, auto_rotate=True)

# Inicializar el auto-closer de ventanas emergentes
auto_closer = CerrarVentanaAutomatica(
    titulos_ventanas=["ERROR", "Error", "error"],
    texto_boton="OK",
    intervalo=0.5  # Revisar cada 500ms para respuesta rápida
)


if Activador_MES == "ON":
    Activador_MES = True
else:
    Activador_MES = False

def crear_monitores(lista_configuraciones): #Para Funcion sin mes
    monitores = []
    for idx, config in enumerate(lista_configuraciones):
        try:
            com_baudrate = config[0].split(":")[1].strip()
            com_in = config[1].split(":")[1].strip()
            com_out = config[2].split(":")[1].strip()
            monitor = SC_SIN_SIM.MonitorSerial(com_in, com_out, com_baudrate, timeout=1)
            monitores.append(monitor)
        except Exception as e:
            print(f"Error al crear monitor para configuración {config}: {e}")
            avisos.fail(f"Error al crear monitor para configuración {config}: {e}")
            Controller_Error.Logs_Error.CapturarEvento("CrearMonitores", f"Configuracion_{idx+1}", str(e))
    return monitores

def obtener_parametros_puertos(lista_configuraciones): #Funcion para el modo con MES
    for idx, config in enumerate(lista_configuraciones):
        try:
            com_baudrate = config[0].split(":")[1].strip()
            com_in = config[1].split(":")[1].strip()
            com_out = config[2].split(":")[1].strip()
            return com_baudrate, com_in, com_out
        except Exception as e:
            print(f"Error al crear monitor para configuración {config}: {e}")
            Controller_Error.Logs_Error.CapturarEvento("Obtener_parametros_main", f"Configuracion_{idx+1}", str(e))

def escribir_en_consola(tag, msg):
    if modo_desarrollador == "ON":
        print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [{tag}] {msg}", flush=True)

def escribir_en_consola_USER(tag, msg):
    if modo_desarrollador == "OFF":
        print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [{tag}] {msg}", flush=True)

def plc_a_pc(PLC_salida, Ventrada, term = b'\r'):
    global activador, esperar_validacion_sn, in00_recibido, out03_recibido, sn_validado, Escaner
    buf = bytearray()
    while activador:
        try:
            n = PLC_salida.in_waiting
            if n:
                chunk = PLC_salida.read(n)
                buf.extend(chunk)
                while True:
                    pos = buf.find(term)
                    if pos == -1:
                        break
                    frame = bytes(buf[:pos+len(term)])
                    del buf[:pos+len(term)]
                    texto = frame.decode('utf-8', errors="ignore").strip()
                    mensajes_recibidos.append(texto)
                    
                    # DETECTAR SEÑALES DEL PLC (lo que el PLC envía a la APP)
                    # Señal 1: IN00 : 1
                    if "IN00 : 1" in texto or "IN00:1" in texto.replace(" ", "") or "in00:1" in texto.lower():
                        in00_recibido = True
                        escribir_en_consola("PLC→APP", f"Señal detectada: {texto}")
                        escribir_en_consola_USER("Abril-SIM", "Señal 1 detectada del PLC (IN00)")
                        
                        # ENVIAR COMANDO "LON" AL ESCÁNER
                        if Escaner and Escaner.is_open:
                            try:
                                Escaner.write(b'LON\r')
                                escribir_en_consola("APP→ESCANER", "Comando enviado: LON")
                                escribir_en_consola_USER("Abril-SIM", "Activando escáner para lectura QR...")
                            except Exception as e:
                                escribir_en_consola("ERROR", f"Error al enviar LON al escáner: {e}")
                                Controller_Error.Logs_Error.CapturarEvento("plc_a_pc", "enviar_LON", str(e))
                        else:
                            escribir_en_consola("ERROR", "Escáner no disponible para enviar comando LON")
                    
                    # Señal 2: OUT03 : ON
                    if "OUT03 : ON" in texto or "OUT03:ON" in texto.replace(" ", "") or "out03:on" in texto.lower():
                        out03_recibido = True
                        escribir_en_consola("PLC→APP", f"Señal detectada: {texto}")
                        
                        # Solo activar espera de SN si ambas señales fueron recibidas y no hay SN validado
                        if in00_recibido and out03_recibido and not sn_validado:
                            esperar_validacion_sn = True
                            escribir_en_consola("APP", " AMBAS SEÑALES RECIBIDAS - SOLICITAR SN")
                            escribir_en_consola_USER("Abril-SIM", "Esperando lectura del escáner...")
                    
                    # Enviar mensaje a la PC (SIEMPRE, sin bloqueos)
                    try:
                        Ventrada.write(frame)
                    except Exception as e:
                        Controller_Error.Logs_Error.CapturarEvento("plc_a_pc", "write", str(e))
        except Exception as e:
            print(e)


os.makedirs(directorio_salida,exist_ok=True)
activador = False
mensajes_recibidos = []
hilo_pc_a_plc = None
hilo_plc_a_pc = None
iniciar_secuencia = False
resultado_secuencia = None
permitir_paso_mensajes = True  # CAMBIADO: Ahora inicia en TRUE (mensajes pasan libremente)
esperar_validacion_sn = False   # NUEVO: Control para esperar SN después de señales PLC
sn_validado = False             # NUEVO: Indica si el SN fue validado
in00_recibido = False           # NUEVO: Flag para IN00 : 1
out03_recibido = False          # NUEVO: Flag para OUT03 : ON
cola_pendientes = queue.Queue()
sn_actual = None
lineas_log = []
Escaner = None  # Puerto serial del escáner

if Activador_MES == False:
    puertos_com = crear_monitores(configuracion)
    print(f"\nMonitores Creados: {len(puertos_com)}")
    for monitor in puertos_com:
        monitor.iniciar()
    try:
        while True:
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n[Debug] Deteniendo el programa manualmente...")
        for monitor in puertos_com:
            monitor.detener()
else:
    valores = obtener_parametros_puertos(configuracion)
    parametros = list(valores)
    com_baudrate = parametros[0]
    com_in = parametros[1]
    com_out = parametros[2]
    
    # Intentar crear los puertos seriales
    puertos_creados_exitosamente = False
    try:
        escribir_en_consola("APP", f"Intentando abrir puerto de entrada: {com_in} @ {com_baudrate}")
        Ventrada = serial.Serial(com_in, com_baudrate, timeout=None)
        escribir_en_consola("APP", f"✓ Puerto de entrada abierto: {com_in}")
        
        escribir_en_consola("APP", f"Intentando abrir puerto de salida: {com_out} @ {com_baudrate}")
        PLC_salida = serial.Serial(com_out, com_baudrate, timeout=None)
        escribir_en_consola("APP", f"✓ Puerto de salida abierto: {com_out}")
        
        # Intentar abrir puerto del escáner
        if puerto_escaner and baudrate_escaner:
            try:
                escribir_en_consola("APP", f"Intentando abrir puerto del escáner: {puerto_escaner} @ {baudrate_escaner}")
                Escaner = serial.Serial(puerto_escaner, baudrate_escaner, timeout=1)
                escribir_en_consola("APP", f"✓ Puerto del escáner abierto: {puerto_escaner}")
            except Exception as e:
                escribir_en_consola("ERROR", f"No se pudo abrir el escáner: {e}")
                escribir_en_consola("APP", "El sistema continuará sin escáner (solo entrada manual)")
                Escaner = None
        else:
            escribir_en_consola("APP", "Configuración del escáner no encontrada. Usando solo entrada manual.")
            Escaner = None
        
        activador = True
        puertos_creados_exitosamente = True
        escribir_en_consola("APP", "✓ Puertos seriales creados exitosamente")
        
        # Iniciar hilo de comunicación PLC a PC
        hilo_plc_a_pc = threading.Thread(target=plc_a_pc, args=(PLC_salida, Ventrada), daemon=True)
        hilo_plc_a_pc.start()
        escribir_en_consola("APP", "✓ Hilo PLC->PC iniciado")
        
    except Exception as e:
        error_msg = str(e)
        Controller_Error.Logs_Error.CapturarEvento("Crear Puertos", "Puerto", error_msg)
        escribir_en_consola("ERROR", f"✗ Error al crear puertos: {error_msg}")
        avisos.fail(
            f"No se pudieron abrir los puertos seriales",
            titulo="Error Crítico - Puertos"
        )
        sys.exit(1)  # Salir del programa con código de error
    
    # Solo continuar si los puertos se crearon exitosamente
    if not puertos_creados_exitosamente:
        sys.exit(1)

    TERM_PC = b'\r'
    buf_entrada = bytearray()
    buf_prioritario = bytearray()
    dejarPasar = set(valores_definidos_taxis)
    sn_queue = queue.Queue()
    lock_sn = threading.RLock()  # RLock permite reentrada desde el mismo hilo
    secuencia_activa = threading.Event()
    mensajes_en_cola = set()  # NUEVO: Tracking de mensajes únicos en cola para evitar duplicados

    def reiniciar_ciclo():
        """Reinicia el ciclo completo para permitir un nuevo SN y reinicia la secuencia del PLC"""
        global iniciar_secuencia, resultado_secuencia, permitir_paso_mensajes, sn_actual, lineas_log
        global esperar_validacion_sn, sn_validado, in00_recibido, out03_recibido, mensajes_en_cola
        
        with lock_sn:
            sn_previo = sn_actual
            iniciar_secuencia = False
            resultado_secuencia = None
            permitir_paso_mensajes = True   # Volver a permitir flujo libre
            esperar_validacion_sn = False   # Reset del flag de espera
            sn_validado = False             # Reset del flag de validación
            in00_recibido = False           # Reset señal IN00
            out03_recibido = False          # Reset señal OUT03
            sn_actual = None
            lineas_log = []
            secuencia_activa.clear()
            mensajes_en_cola.clear()        # NUEVO: Limpiar tracking de mensajes
            # Limpiar cola pendientes
            while not cola_pendientes.empty():
                try:
                    cola_pendientes.get_nowait()
                except:
                    break
        
        # ENVIAR COMANDOS DE RESET AL PLC
        escribir_en_consola("APP", "Enviando comandos de reset al PLC...")
        comandos_reset = [
            b'4od\r',   # Apagar OUT04
            b'9in\r',   # Leer IN09
            b'3od\r',   # Apagar OUT03 (señal crítica del atornillado)
            b'5in\r',   # Leer IN05
            b'7in\r'    # Leer IN07
        ]
        
        try:
            for idx, comando in enumerate(comandos_reset, 1):
                PLC_salida.write(comando)
                escribir_en_consola("APP→PLC", f"Reset {idx}/5: {comando.decode('utf-8').strip()}")
                time.sleep(0.05)  # Pequeña pausa entre comandos
            escribir_en_consola("APP", "✓ Comandos de reset enviados al PLC")
        except Exception as e:
            escribir_en_consola("ERROR", f"Error al enviar comandos de reset al PLC: {e}")
            Controller_Error.Logs_Error.CapturarEvento("reiniciar_ciclo", "enviar_reset_plc", str(e))
        
        escribir_en_consola("Abril-SIM", f"Ciclo reiniciado (SN previo: {sn_previo}). Listo para nuevo SN.")
        escribir_en_consola_USER("Abril-SIM", "Sistema listo para siguiente SN.")

    def leer_escaner_async():
        """Hilo para leer datos del escáner por puerto serial"""
        global Escaner, activador
        
        escribir_en_consola("APP", "Hilo leer_escaner_async iniciado")
        buf_escaner = bytearray()
        
        while activador:
            try:
                if not Escaner or not Escaner.is_open:
                    time.sleep(0.1)
                    continue
                
                # Leer datos del escáner
                n = Escaner.in_waiting
                if n > 0:
                    chunk = Escaner.read(n)
                    buf_escaner.extend(chunk)
                    
                    # Buscar terminador (puede ser \r o \n dependiendo del escáner)
                    while True:
                        pos_r = buf_escaner.find(b'\r')
                        pos_n = buf_escaner.find(b'\n')
                        
                        # Encontrar el primer terminador
                        if pos_r == -1 and pos_n == -1:
                            break
                        
                        pos = pos_r if pos_r != -1 and (pos_n == -1 or pos_r < pos_n) else pos_n
                        term_len = 1
                        
                        # Extraer el código
                        codigo = bytes(buf_escaner[:pos]).decode('utf-8', errors='ignore').strip()
                        del buf_escaner[:pos + term_len]
                        
                        # Si hay código válido, enviarlo a la cola
                        if codigo and len(codigo) > 0:
                            escribir_en_consola("ESCANER→APP", f"Código leído: {codigo}")
                            sn_queue.put(codigo)
                
                time.sleep(0.01)
                
            except Exception as e:
                escribir_en_consola("ERROR", f"Error en leer_escaner: {e}")
                Controller_Error.Logs_Error.CapturarEvento("leer_escaner_async", "loop", str(e))
                time.sleep(0.1)
    
    def pedir_sn_async():
        """Hilo para pedir SN de forma asíncrona (entrada manual de respaldo)"""
        import sys
        import msvcrt  # Para leer caracteres sin Enter en Windows
        
        while activador:
            try:
                sn_buffer = ""
                prompt_mostrado = False
                ultimo_char_time = time.time()
                
                while activador:
                    # Mostrar prompt solo cuando se detecta espera de SN
                    if esperar_validacion_sn and not prompt_mostrado:
                        print("\n[Manual] Pickeo de SN: ", end='', flush=True)
                        prompt_mostrado = True
                    
                    # Leer un caracter a la vez (sin esperar Enter)
                    if msvcrt.kbhit():
                        char = msvcrt.getch()
                        
                        # Mostrar prompt si se empieza a escribir y no estaba mostrado
                        if not prompt_mostrado and len(sn_buffer) == 0:
                            print("\n[Manual] Pickeo de SN: ", end='', flush=True)
                            prompt_mostrado = True
                        
                        # Enter manual (si el usuario lo presiona)
                        if char in (b'\r', b'\n'):
                            if sn_buffer.strip():
                                print()  # Nueva línea
                                sn_queue.put(sn_buffer.strip())
                                prompt_mostrado = False
                            break
                        
                        # Backspace
                        elif char == b'\x08':
                            if len(sn_buffer) > 0:
                                sn_buffer = sn_buffer[:-1]
                                # Borrar el último caracter en pantalla
                                print('\b \b', end='', flush=True)
                        
                        # Caracter normal
                        else:
                            try:
                                decoded_char = char.decode('utf-8')
                                sn_buffer += decoded_char
                                print(decoded_char, end='', flush=True)
                                ultimo_char_time = time.time()
                            except:
                                pass
                    
                    # AUTO-ENTER: Si han pasado más de 100ms sin nuevos caracteres y hay buffer
                    # Esto detecta cuando el escáner terminó de enviar el SN
                    if len(sn_buffer) > 0 and (time.time() - ultimo_char_time) > 0.1:
                        print()  # Nueva línea
                        sn_queue.put(sn_buffer.strip())
                        prompt_mostrado = False
                        break
                    
                    time.sleep(0.01)  # Pequeña pausa para no saturar CPU
                    
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                escribir_en_consola("INPUT_SN", f"Error en entrada: {e}")
                time.sleep(0.1)
    
    # Diccionario global para almacenar datos de BREQ por SN
    breq_data_store = {}
    
    def procesar_sn_async():
        """Hilo para procesar SNs desde la cola"""
        global permitir_paso_mensajes, sn_actual, lineas_log, breq_data_store
        global esperar_validacion_sn, sn_validado
        
        escribir_en_consola("APP", "Hilo procesar_sn_async iniciado")
        
        while activador:
            try:
                # Solo procesar SN cuando se solicite (después de las señales del PLC)
                if not esperar_validacion_sn:
                    time.sleep(0.1)
                    continue
                
                # Esperar un SN de la cola (bloqueante con timeout)
                try:
                    sn_texto = sn_queue.get(timeout=0.5)
                    escribir_en_consola("APP", f"SN obtenido de la cola: {sn_texto}")
                except queue.Empty:
                    continue
                
                # Verificar si hay una secuencia activa
                with lock_sn:
                    if sn_actual is not None and sn_validado:
                        escribir_en_consola_USER("Abril-SIM", f"SN [{sn_actual}] en proceso. Esperá a que termine el ciclo.")
                        escribir_en_consola("APP", f"SN rechazado: {sn_texto} (hay secuencia activa)")
                        
                        # Mostrar popup al usuario
                        mostrar_popup_timeout(
                            f"SN rechazado: {sn_texto}\n\nHay una secuencia activa con SN [{sn_actual}]\n\nEsperá a que termine el ciclo actual.",
                            titulo="Secuencia en Progreso"
                        )
                        
                        # LIMPIAR LA COLA DE SNs PARA EVITAR ACUMULACIÓN
                        sn_descartados = 0
                        while not sn_queue.empty():
                            try:
                                sn_queue.get_nowait()
                                sn_descartados += 1
                            except queue.Empty:
                                break
                        continue
                
                # Procesar el nuevo SN
                escribir_en_consola("APP", f"Procesando SN: {sn_texto}")
                escribir_en_consola_USER("Abril-SIM", f"Validando SN: {sn_texto}...")
                
                try:
                    consultas_sim = CS.Consultas_SIM(sn_texto)
                    ok_breq, breq_msg, breq_resp = consultas_sim._check_sn()
                except Exception as e:
                    Controller_Error.Logs_Error.CapturarEvento("procesar_sn", "check_sn", str(e))
                    ok_breq = False
                    breq_msg = "ERROR"
                    breq_resp = str(e)
                    escribir_en_consola_USER("Abril-SIM", f"Error al validar SN: {e}")
                    mostrar_popup_fail(f"Error al validar SN [{sn_texto}] \n{breq_resp}", titulo="Error BREQ")
                    
                    # CERRAR VENTANAS DE ERROR AUTOMÁTICAMENTE
                    escribir_en_consola("APP", "Intentando cerrar ventanas de error...")
                    time.sleep(0.5)  # Esperar a que aparezca la ventana
                    auto_closer.cerrar_ventana_ahora("ERROR")
                    auto_closer.cerrar_ventana_ahora("Error")
                    auto_closer.cerrar_ventana_ahora("TIMEOUT")
                    
                    # Resetear flags para permitir nuevo intento
                    with lock_sn:
                        esperar_validacion_sn = False
                        sn_validado = False
                    continue
                
                # Actualizar estado global
                with lock_sn:
                    if ok_breq:
                        sn_actual = sn_texto
                        lineas_log = []
                        sn_validado = True              # SN validado correctamente
                        esperar_validacion_sn = False   # Ya no esperar más validación
                        permitir_paso_mensajes = True   # Permitir mensajes
                        secuencia_activa.set()
                        
                        # GUARDAR DATOS DE BREQ PARA EL LOG
                        breq_data_store[sn_actual] = (ok_breq, breq_msg, breq_resp)
                        
                        escribir_en_consola("APP", f"✓ SN válido: {sn_actual} - Continuando secuencia")
                        escribir_en_consola_USER("Abril-SIM", f"✓ SN [{sn_actual}] aceptado. Continuando prueba...")
                        mostrar_popup_pass(
                            f"SN [{sn_actual}] validado correctamente",
                            titulo="✓ SN Aceptado"
                        )
                        
                        # Enviar mensajes pendientes (si hay)
                        mensajes_enviados = 0
                        mensajes_unicos_enviados = set()
                        while not cola_pendientes.empty():
                            try:
                                frame_p = cola_pendientes.get_nowait()
                                texto_p = frame_p.decode('utf-8', errors='ignore').strip()
                                
                                # Solo enviar si no se ha enviado antes (evitar duplicados)
                                if texto_p not in mensajes_unicos_enviados:
                                    PLC_salida.write(frame_p)
                                    mensajes_unicos_enviados.add(texto_p)
                                    mensajes_enviados += 1
                                    escribir_en_consola("APP", f"  → Enviando mensaje pendiente: {texto_p}")
                            except Exception as e:
                                Controller_Error.Logs_Error.CapturarEvento("procesar_sn", "enviar_pendientes", str(e))
                        
                        # Limpiar tracking después de enviar
                        with lock_sn:
                            mensajes_en_cola.clear()
                        
                        if mensajes_enviados > 0:
                            escribir_en_consola("APP", f"✓ Enviados {mensajes_enviados} mensajes únicos pendientes")
                    else:
                        escribir_en_consola("APP", f"✗ SN rechazado: {sn_texto} - {breq_msg}")
                        escribir_en_consola("APP", f"   Respuesta completa BREQ: {breq_resp}")
                        escribir_en_consola_USER("Abril-SIM", f"✗ SN [{sn_texto}] rechazado por SIM.")
                        mostrar_popup_fail(f"Porfavor Retire la Placa \n\n {sn_texto} rechazado:\n{breq_msg}\n", titulo="SN Inválido")
                        
                        # CERRAR VENTANAS DE ERROR/TIMEOUT AUTOMÁTICAMENTE
                        escribir_en_consola("APP", "Cerrando ventanas de error automáticamente...")
                        time.sleep(1.0)  # Esperar a que aparezcan las ventanas
                        
                        # Intentar cerrar múltiples tipos de ventanas de error
                        ventanas_cerradas = 0
                        for titulo in ["ERROR", "Error", "TIMEOUT", "Timeout", "Warning", "Advertencia"]:
                            if auto_closer.cerrar_ventana_ahora(titulo):
                                ventanas_cerradas += 1
                        
                        if ventanas_cerradas > 0:
                            escribir_en_consola("APP", f"✓ {ventanas_cerradas} ventana(s) de error cerrada(s) automáticamente")
                        
                        # GUARDAR LOG DE BREQ RECHAZADO
                        try:
                            logger.save_breq_bcmp(
                                sn=sn_texto,
                                breq_tuple=(ok_breq, breq_msg, breq_resp),
                                bcmp_tuple=None,
                                is_pass=False
                            )
                            escribir_en_consola("APP", f"Log guardado para SN rechazado: {sn_texto}")
                        except Exception as e:
                            escribir_en_consola("ERROR", f"Error al guardar log: {e}")
                            Controller_Error.Logs_Error.CapturarEvento("procesar_sn", "guardar_log_breq", str(e))
                        
                        # LIMPIAR COLA DE MENSAJES PENDIENTES
                        mensajes_descartados = 0
                        with lock_sn:
                            while not cola_pendientes.empty():
                                try:
                                    cola_pendientes.get_nowait()
                                    mensajes_descartados += 1
                                except:
                                    break
                            mensajes_en_cola.clear()  # Limpiar tracking de mensajes
                        
                        if mensajes_descartados > 0:
                            escribir_en_consola("APP", f"✓ Cola limpiada: {mensajes_descartados} mensajes descartados")
                        else:
                            escribir_en_consola("APP", "✓ No había mensajes pendientes para descartar")
                        
                        # OPCIÓN B: REINICIAR CICLO COMPLETO AL RECHAZAR SN
                        escribir_en_consola("APP", "═══════════════════════════════════════════")
                        escribir_en_consola("APP", "║  SN RECHAZADO - REINICIANDO CICLO      ║")
                        escribir_en_consola("APP", "═══════════════════════════════════════════")
                        escribir_en_consola_USER("Abril-SIM", "Ingrese una Nueva Placa. Listo Para un nuevo Intento")
                        
                        # Llamar a reiniciar_ciclo para resetear todo
                        reiniciar_ciclo()
                        
            except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("procesar_sn_async", "loop", str(e))
                time.sleep(0.1)

    def hilo_mensajes_entrada():
        """Hilo para procesar mensajes de entrada PC→PLC - BLOQUEA SI ESPERA VALIDACIÓN SN (excepto mensajes críticos)"""
        global iniciar_secuencia, resultado_secuencia, sn_actual, sn_validado, esperar_validacion_sn, mensajes_en_cola
        
        while activador:
            try:
                n = Ventrada.in_waiting
                if not n:
                    time.sleep(0.003)
                    continue

                chunk = Ventrada.read(n)
                if not chunk:
                    continue

                buf_entrada.extend(chunk)
                
                # Procesar frames completos
                while True:
                    pos = buf_entrada.find(TERM_PC)
                    if pos == -1:
                        break
                    
                    frame = bytes(buf_entrada[:pos + len(TERM_PC)])
                    del buf_entrada[:pos + len(TERM_PC)]
                    texto = frame.decode('utf-8', errors='ignore').strip()
                    
                    if not texto:
                        continue
                    
                    # VERIFICAR SI ES UN MENSAJE CRÍTICO (valores_definidos_taxis)
                    es_mensaje_critico = texto in dejarPasar
                    
                    # VERIFICAR SI SE DEBE BLOQUEAR EL FLUJO
                    with lock_sn:
                        esperando_sn = esperar_validacion_sn
                        sn_ok = sn_validado
                    
                    # SI ESTÁ ESPERANDO VALIDACIÓN Y NO HAY SN VALIDADO: BLOQUEAR (excepto mensajes críticos)
                    if esperando_sn and not sn_ok and not es_mensaje_critico:
                        # DEDUPLICACIÓN: Solo agregar a la cola si NO está ya presente
                        with lock_sn:
                            if texto not in mensajes_en_cola:
                                cola_pendientes.put(frame)
                                mensajes_en_cola.add(texto)
                                escribir_en_consola("APP", f"⏸ Mensaje bloqueado (esperando SN): {texto}")
                        continue
                    
                    # ENVIAR MENSAJE AL PLC
                    try:
                        PLC_salida.write(frame)
                    except Exception as e:
                        Controller_Error.Logs_Error.CapturarEvento("hilo_entrada", "write", str(e))
                    
                    # Detectar eventos de la secuencia (solo si SN está validado)
                    with lock_sn:
                        validado = sn_validado
                        sn_proc = sn_actual
                    
                    if validado and sn_proc:
                        if texto == "3oe":
                            with lock_sn:
                                iniciar_secuencia = True
                            escribir_en_consola("APP", f"Secuencia iniciada (3oe) para SN [{sn_proc}]")
                            escribir_en_consola_USER("Abril-SIM", f"Secuencia en progreso para SN [{sn_proc}]")
                        
                        elif texto == "10oe":
                            with lock_sn:
                                resultado_secuencia = "FAIL"
                            escribir_en_consola("APP", f"Resultado = FAIL (10oe) para SN [{sn_proc}]")
                            escribir_en_consola_USER("Abril-SIM", f"Test FAIL para SN [{sn_proc}]")
                            procesar_resultado_bcmp()
                        
                        elif texto == "12oe":
                            with lock_sn:
                                resultado_secuencia = "PASS"
                            escribir_en_consola("APP", f"Resultado = PASS (12oe) para SN [{sn_proc}]")
                            escribir_en_consola_USER("Abril-SIM", f"Test PASS para SN [{sn_proc}]")
                            procesar_resultado_bcmp()
                        
            except Exception as e:
                escribir_en_consola("ERROR", f"Error en hilo_entrada: {e}")
                Controller_Error.Logs_Error.CapturarEvento("hilo_entrada", "loop", str(e))
                time.sleep(0.02)
    
    def procesar_resultado_bcmp():
        """Procesa el resultado PASS/FAIL y envía BCMP"""
        global sn_actual, resultado_secuencia, breq_data_store
        
        with lock_sn:
            resultado = resultado_secuencia
            sn_proc = sn_actual
        
        if resultado not in ("PASS", "FAIL") or not sn_proc:
            return
        
        escribir_en_consola("APP", f"Enviando BCMP para SN [{sn_proc}] con resultado {resultado}...")
        
        ok_bcmp = None
        bcmp_msg = ""
        bcmp_resp = ""
        
        try:
            consultas = CS.Consultas_SIM(sn_proc)
            ok_bcmp, bcmp_msg, bcmp_resp = consultas._check_bcmp(resultado)

        except Exception as e:
            Controller_Error.Logs_Error.CapturarEvento("procesar_bcmp", "check_bcmp", str(e))
            ok_bcmp = False
            bcmp_msg = f"BCMP|ERROR"
            bcmp_resp = str(e)
            escribir_en_consola_USER("Abril-SIM", f"Error al enviar BCMP: {e}")
            mostrar_popup_fail(f"No se pudo enviar el BCMP para SN [{sn_proc}]:\n{str(e)}", titulo="Error BCMP")
        
        respuesta_bcmp = bool(ok_bcmp)
        
        # GUARDAR LOG CON BREQ Y BCMP
        try:
            # Obtener datos de BREQ guardados previamente
            breq_tuple = breq_data_store.get(sn_proc, (False, "BREQ|NO_DATA", "NO_DATA"))
            
            # Guardar log completo
            log_path = logger.save_breq_bcmp(
                sn=sn_proc,
                breq_tuple=breq_tuple,
                bcmp_tuple=(ok_bcmp, bcmp_msg, bcmp_resp),
                is_pass=(resultado == "PASS" and respuesta_bcmp)
            )
            escribir_en_consola("APP", f"✓ Log guardado en: {log_path}")
            
            # Limpiar datos de BREQ después de guardar
            if sn_proc in breq_data_store:
                del breq_data_store[sn_proc]
                
        except Exception as e:
            escribir_en_consola("ERROR", f"Error al guardar log: {e}")
            Controller_Error.Logs_Error.CapturarEvento("procesar_bcmp", "guardar_log", str(e))
        
        # MOSTRAR POP-UPS Y MENSAJES SEGÚN RESULTADO
        if respuesta_bcmp:
            # BCMP ACEPTADO
            escribir_en_consola("APP", f"✓ BCMP aceptado para SN [{sn_proc}] con {resultado}")
            escribir_en_consola_USER("Abril-SIM", f"✓ BCMP enviado exitosamente para SN [{sn_proc}]")
            
            # Pop-up según el resultado del test
            if resultado == "PASS":
                mostrar_popup_pass(
                    f"✓ Test APROBADO\n\nSN: {sn_proc}\nResultado: PASS\nBCMP: Aceptado\n\nSIM: {bcmp_resp}",
                    titulo="✓ Test PASS - BCMP Aceptado"
                )
            else:  # resultado == "FAIL"
                mostrar_popup_fail(
                    f"✗ Test REPROBADO\n\nSN: {sn_proc}\nResultado: FAIL\nBCMP: Aceptado\n\nSIM: {bcmp_resp}",
                    titulo="✗ Test FAIL - BCMP Aceptado"
                )
        else:
            # BCMP RECHAZADO
            escribir_en_consola("APP", f"✗ BCMP rechazado para SN [{sn_proc}] con {resultado}: {bcmp_msg}")
            escribir_en_consola_USER("Abril-SIM", f"✗ BCMP rechazado: {bcmp_msg}")
            
            # Siempre mostrar popup de error cuando BCMP es rechazado
            mostrar_popup_fail(
                f"✗ BCMP RECHAZADO\n\nSN: {sn_proc}\nResultado del test: {resultado}\n\nMotivo: {bcmp_msg}\n\nSIM: {bcmp_resp}",
                titulo="✗ Error - BCMP Rechazado"
            )
        
        reiniciar_ciclo()


    print("""
        
░█████╗░██████╗░██████╗░██╗██╗░░░░░  ░░░░░░  ░██████╗██╗███╗░░░███╗
██╔══██╗██╔══██╗██╔══██╗██║██║░░░░░  ░░░░░░  ██╔════╝██║████╗░████║
███████║██████╦╝██████╔╝██║██║░░░░░  █████╗  ╚█████╗░██║██╔████╔██║
██╔══██║██╔══██╗██╔══██╗██║██║░░░░░  ╚════╝  ░╚═══██╗██║██║╚██╔╝██║
██║░░██║██████╦╝██║░░██║██║███████╗  ░░░░░░  ██████╔╝██║██║░╚═╝░██║
╚═╝░░╚═╝╚═════╝░╚═╝░░╚═╝╚═╝╚══════╝  ░░░░░░  ╚═════╝░╚═╝╚═╝░░░░░╚═╝

        """)
    # Iniciar hilos
    escribir_en_consola("APP", "Iniciando hilos del sistema...")
    
    # Configurar y iniciar auto-closer de ventanas
    auto_closer.set_log_callback(escribir_en_consola)
    auto_closer.iniciar()
    escribir_en_consola("APP", "✓ Auto-closer de ventanas ERROR iniciado")
    
    # Hilo para leer del escáner (si está disponible)
    if Escaner:
        hilo_escaner = threading.Thread(target=leer_escaner_async, daemon=True, name="LeerEscaner")
        hilo_escaner.start()
        escribir_en_consola("APP", "✓ Hilo de lectura del escáner iniciado")
    
    # Hilo de entrada manual (respaldo)
    hilo_input_sn = threading.Thread(target=pedir_sn_async, daemon=True, name="InputSN")
    hilo_input_sn.start()
    escribir_en_consola("APP", "✓ Hilo de entrada manual SN iniciado")
    
    hilo_procesador_sn = threading.Thread(target=procesar_sn_async, daemon=True, name="ProcesarSN")
    hilo_procesador_sn.start()
    escribir_en_consola("APP", "✓ Hilo procesador de SN iniciado")
    
    hilo_entrada = threading.Thread(target=hilo_mensajes_entrada, daemon=True, name="MensajesEntrada")
    hilo_entrada.start()
    escribir_en_consola("APP", "✓ Hilo de mensajes de entrada iniciado")
    
    escribir_en_consola_USER("Abril-SIM", "Sistema listo. Esperando SN...")
    escribir_en_consola("APP", "Sistema MES activo. Todos los hilos en ejecución.")
    
    # Bucle principal de monitoreo
    try:
        while activador:
            procesar_popups()  # Procesar pop-ups pendientes desde hilos
            root.update()  # Procesar eventos de tkinter
            time.sleep(0.1)  # Evitar consumo excesivo de CPU
    except KeyboardInterrupt:
        escribir_en_consola("APP", "Interrupción manual detectada. Cerrando...")
        activador = False
        try:
            # Detener auto-closer
            auto_closer.detener()
            escribir_en_consola("APP", "Auto-closer detenido")
            
            if Ventrada and Ventrada.is_open:
                Ventrada.close()
                escribir_en_consola("APP", "Puerto de entrada cerrado")
            if PLC_salida and PLC_salida.is_open:
                PLC_salida.close()
                escribir_en_consola("APP", "Puerto de salida cerrado")
            if Escaner and Escaner.is_open:
                Escaner.close()
                escribir_en_consola("APP", "Puerto del escáner cerrado")
        except Exception as e:
            escribir_en_consola("ERROR", f"Error al cerrar puertos: {e}")
        escribir_en_consola("APP", "Aplicación terminada.")
    except Exception as e:
        Controller_Error.Logs_Error.CapturarEvento("main", "loop_principal", str(e))
        escribir_en_consola("ERROR", f"Error crítico en bucle principal: {e}")
        activador = False
        try:
            # Detener auto-closer
            auto_closer.detener()
            
            if Ventrada and Ventrada.is_open:
                Ventrada.close()
            if PLC_salida and PLC_salida.is_open:
                PLC_salida.close()
            if Escaner and Escaner.is_open:
                Escaner.close()
        except:
            pass

        