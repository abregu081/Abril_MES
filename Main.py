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

root = tk.Tk()
root.withdraw()
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

def mostrar_popup_pass(mensaje, titulo="Éxito"):
    """Encola un popup de éxito para mostrarlo en el hilo principal"""
    popup_queue.put({'tipo': 'pass', 'mensaje': mensaje, 'titulo': titulo})

configuracion, modo_desarrollador = ST.Setting.obtener_puertos_comunicaciones()
configuracion_MES = ST.Setting.obtener_parametros_MES()
valores_definidos_taxis = ST.Setting.obtener_Comandos_PLC()
Activador_MES = configuracion_MES["habilitar_mes"]
directorio_salida = configuracion_MES["directorio_logs"]

# Inicializar el gestor de logs
logger = LG.LogManager(directorio_salida, auto_rotate=True)

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

def plc_a_pc(PLC_salida,Ventrada, term = b'\r'):
    global activador
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
                    try:
                        Ventrada.write(frame)
                    except Exception as e:
                            Controller_Error.Logs_Error.CapturarEvento("", "plc2pc.write", str(e))
        except Exception as e:
                print(e)


os.makedirs(directorio_salida,exist_ok=True)
activador = False
mensajes_recibidos = []
hilo_pc_a_plc = None
hilo_plc_a_pc = None
iniciar_secuencia = False
resultado_secuencia = None
permitir_paso_mensajes = False
cola_pendientes = queue.Queue()
sn_actual = None
lineas_log = []

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

    def reiniciar_ciclo():
        """Reinicia el ciclo completo para permitir un nuevo SN"""
        global iniciar_secuencia, resultado_secuencia, permitir_paso_mensajes, sn_actual, lineas_log
        with lock_sn:
            sn_previo = sn_actual
            iniciar_secuencia = False
            resultado_secuencia = None
            permitir_paso_mensajes = False
            sn_actual = None
            lineas_log = []
            secuencia_activa.clear()
            # Limpiar cola pendientes
            while not cola_pendientes.empty():
                try:
                    cola_pendientes.get_nowait()
                except:
                    break
        escribir_en_consola("Abril-SIM", f"Ciclo reiniciado (SN previo: {sn_previo}). Listo para nuevo SN.")
        escribir_en_consola_USER("Abril-SIM", "Sistema listo para siguiente SN.")

    def pedir_sn_async():
        """Hilo para pedir SN de forma asíncrona"""
        while activador:
            try:
                sys.stdout.flush()
                sn_in = input("Pickeo de SN: ").strip()
                if sn_in:
                    sn_queue.put(sn_in)
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
        
        escribir_en_consola("APP", "Hilo procesar_sn_async iniciado")
        
        while activador:
            try:
                # Esperar un SN de la cola (bloqueante con timeout)
                try:
                    sn_texto = sn_queue.get(timeout=0.5)
                    escribir_en_consola("APP", f"SN obtenido de la cola: {sn_texto}")
                except queue.Empty:
                    continue
                
                # Verificar si hay una secuencia activa
                with lock_sn:
                    estado_actual = (sn_actual, permitir_paso_mensajes)
                    if sn_actual is not None and permitir_paso_mensajes:
                        escribir_en_consola_USER("Abril-SIM", f"SN [{sn_actual}] en proceso. Esperá a que termine el ciclo.")
                        escribir_en_consola("APP", f"SN rechazado: {sn_texto} (hay secuencia activa)")
                        continue
                
                escribir_en_consola("APP", f"Estado antes de procesar: sn_actual={estado_actual[0]}, permitir={estado_actual[1]}")
                
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
                    mostrar_popup_fail(f"Error al validar SN [{sn_texto}]", titulo="Error BREQ")
                    continue
                
                # Actualizar estado global
                with lock_sn:
                    if ok_breq:
                        sn_actual = sn_texto
                        lineas_log = []
                        permitir_paso_mensajes = True
                        secuencia_activa.set()
                        
                        # GUARDAR DATOS DE BREQ PARA EL LOG
                        breq_data_store[sn_actual] = (ok_breq, breq_msg, breq_resp)
                        
                        escribir_en_consola("APP", f"✓ SN válido: {sn_actual} - Semáforo VERDE")
                        escribir_en_consola_USER("Abril-SIM", f"✓ SN [{sn_actual}] aceptado. Esperando secuencia...")
                        mostrar_popup_pass(
                            f"BREQ aceptado para SN [{sn_actual}]\nResultado: {breq_data_store[breq_resp]}",
                            titulo="✓ BREQ Aceptado"
                        )
                        # Enviar mensajes pendientes
                        mensajes_enviados = 0
                        while not cola_pendientes.empty():
                            try:
                                frame_p = cola_pendientes.get_nowait()
                                PLC_salida.write(frame_p)
                                mensajes_enviados += 1
                            except Exception as e:
                                Controller_Error.Logs_Error.CapturarEvento("procesar_sn", "enviar_pendientes", str(e))
                        
                        if mensajes_enviados > 0:
                            escribir_en_consola("APP", f"Enviados {mensajes_enviados} mensajes pendientes")
                    else:
                        escribir_en_consola("APP", f"✗ SN rechazado: {sn_texto} - {breq_msg}")
                        escribir_en_consola_USER("Abril-SIM", f"✗ SN [{sn_texto}] rechazado: {breq_msg}")
                        mostrar_popup_fail(f"SN [{sn_texto}] rechazado:\n{breq_msg}", titulo="SN Inválido")
                        
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
                
                # Reiniciar ciclo FUERA del lock cuando el SN es rechazado
                if not ok_breq:
                    reiniciar_ciclo()
                        
            except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("procesar_sn_async", "loop", str(e))
                time.sleep(0.1)

    def hilo_mensajes_entrada():
        """Hilo principal para procesar mensajes de entrada y lógica de secuencia"""
        global iniciar_secuencia, resultado_secuencia, sn_actual, permitir_paso_mensajes
        
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
                    
                    # Mensajes prioritarios SIEMPRE pasan
                    if texto in dejarPasar:
                        try:
                            PLC_salida.write(frame)
                            #escribir_en_consola("PRIORITARIO", f"→ {texto}")
                        except Exception as e:
                            Controller_Error.Logs_Error.CapturarEvento("hilo_entrada", "write_prioritario", str(e))
                        continue
                    
                    # Mensajes normales: dependen del semáforo
                    with lock_sn:
                        paso_permitido = permitir_paso_mensajes
                        sn_proc = sn_actual
                    
                    if paso_permitido:
                        try:
                            PLC_salida.write(frame)
                            escribir_en_consola("NORMAL", f"→ {texto}")
                        except Exception as e:
                            Controller_Error.Logs_Error.CapturarEvento("hilo_entrada", "write_normal", str(e))
                        
                        # Detectar eventos de la secuencia
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
                    else:
                        # Sin SN válido: encolar mensaje
                        cola_pendientes.put(frame)
                        escribir_en_consola("COLA", f"Encolado: {texto} (esperando SN válido)")
                        
            except Exception as e:
                #Controller_Error.Logs_Error.CapturarEvento("hilo_entrada", "loop", str(e))
                escribir_en_consola("ERROR", f"Error en hilo_entrada: {e}")
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
        
        # Mostrar pop-ups y mensajes
        if respuesta_bcmp:
            escribir_en_consola("APP", f"✓ BCMP aceptado para SN [{sn_proc}] con {resultado}")
            escribir_en_consola_USER("Abril-SIM", f"✓ BCMP enviado exitosamente para SN [{sn_proc}]")
            try:
                mostrar_popup_pass(
                    f"BCMP aceptado para SN [{sn_proc}]\nResultado: {resultado}",
                    titulo="✓ BCMP Aceptado"
                )
            except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("procesar_bcmp", "popup_pass", str(e))
        else:
            escribir_en_consola("APP", f"✗ BCMP rechazado para SN [{sn_proc}] con {resultado}: {bcmp_msg}")
            escribir_en_consola_USER("Abril-SIM", f"✗ BCMP rechazado: {bcmp_msg}")
            mostrar_popup_fail(
                f"BCMP rechazado para SN [{sn_proc}]{bcmp_resp}",
                titulo="BCMP Rechazado"
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
    
    hilo_input_sn = threading.Thread(target=pedir_sn_async, daemon=True, name="InputSN")
    hilo_input_sn.start()
    escribir_en_consola("APP", "✓ Hilo de entrada SN iniciado")
    
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
            if Ventrada and Ventrada.is_open:
                Ventrada.close()
                escribir_en_consola("APP", "Puerto de entrada cerrado")
            if PLC_salida and PLC_salida.is_open:
                PLC_salida.close()
                escribir_en_consola("APP", "Puerto de salida cerrado")
        except Exception as e:
            escribir_en_consola("ERROR", f"Error al cerrar puertos: {e}")
        escribir_en_consola("APP", "Aplicación terminada.")
    except Exception as e:
        Controller_Error.Logs_Error.CapturarEvento("main", "loop_principal", str(e))
        escribir_en_consola("ERROR", f"Error crítico en bucle principal: {e}")
        activador = False
        try:
            if Ventrada and Ventrada.is_open:
                Ventrada.close()
            if PLC_salida and PLC_salida.is_open:
                PLC_salida.close()
        except:
            pass