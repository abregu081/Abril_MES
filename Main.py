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
import LogCreator as LG

configuracion, modo_desarrollador = ST.Setting.obtener_puertos_comunicaciones()
configuracion_MES = ST.Setting.obtener_parametros_MES()
valores_definidos_taxis = ["16in", "ec", "0in"]
Activador_MES = configuracion_MES["habilitar_mes"]
directorio_salida = configuracion_MES["directorio_logs"]
if Activador_MES == "ON":
    Activador_MES = True

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
            print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [{tag}] {msg}")

def escribir_en_consola_USER(tag, msg):
        if modo_desarrollador == "OFF":
            print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [{tag}] {msg}")

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
                    escribir_en_consola("PLC--->Abril_SIM", f"{texto!r}")
                    try:
                        Ventrada.write(frame)
                    except Exception as e:
                            Controller_Error.Logs_Error.CapturarEvento("", "plc2pc.write", str(e))
        except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "_loop_plc2pc", str(e))

def _append_log(sn: str, msg: str):
    # Formato: SN<TAB>mensaje
    lineas_log.append(f"{sn}\t{msg}")



os.makedirs(directorio_salida,exist_ok=True)
logger = LG.LogManager(directorio_salida)
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
    try:
        Ventrada = serial.Serial(com_in,com_baudrate,timeout=1) #Crear los puertos
        PLC_salida = serial.Serial(com_out,com_baudrate,timeout=1)
        activador = True
        hilo_plc_a_pc = threading.Thread(target=plc_a_pc,args=(PLC_salida, Ventrada), daemon=True)
        hilo_plc_a_pc.start()
    except Exception as e:
        Controller_Error.Logs_Error.CapturarEvento("Crear Puertos", "Puerto",str(e))

    TERM_PC = b'\r'
    buf = bytearray()
    dejarPasar = set(valores_definidos_taxis)
    sn_queue = queue.Queue()

    def pedir_sn_async():
        while True:
            try:
                sn_in = input("Pickeo de SN : ").strip()
                sn_queue.put(sn_in)
            except (EOFError, KeyboardInterrupt):
                break

    threading.Thread(target=pedir_sn_async, daemon=True).start()

    def procesar_sn(sn_texto: str):
        global permitir_paso_mensajes, sn_actual, lineas_log
        sn_actual = sn_texto
        lineas_log = []  # iniciar log para este SN

        try:
            ok_breq, breq_msg, breq_resp = CS.Consultas_SIM._check_sn(sn_actual)
        except Exception as e:
            Controller_Error.Logs_Error.CapturarEvento("main.pc2plc", "check_sn", str(e))
            ok_breq, breq_msg, breq_resp = False, f"BREQ(ERROR_BUILD)|id={sn_actual}", f"ERROR:{e}"

        # Grabar en memoria (luego se guarda a disco al cerrar ciclo con BCMP)
        _append_log(sn_actual, breq_msg)
        _append_log(sn_actual, breq_resp)

        permitir_paso_mensajes = bool(ok_breq)
        if permitir_paso_mensajes:
            while not cola_pendientes.empty():
                frame_p = cola_pendientes.get_nowait()
                try:
                    PLC_salida.write(frame_p)
                    tpend = frame_p.decode('utf-8', errors='ignore').strip()
                    escribir_en_consola("[Abril_SIM]---->PLC", f"{tpend!r}")
                except Exception as e:
                    Controller_Error.Logs_Error.CapturarEvento("main.pc2plc", "write.cola", str(e))
    
    def reiniciar_ciclo():
        global iniciar_secuencia, resultado_secuencia, permitir_paso_mensajes, sn_actual, buf, lineas_log
        iniciar_secuencia = False
        resultado_secuencia = None
        permitir_paso_mensajes = False
        sn_actual = None
        lineas_log = []
        while not cola_pendientes.empty():
            try:
                cola_pendientes.get_nowait()
            except:
                break

    try:
        sn_boot = sn_queue.get_nowait()
        procesar_sn(sn_boot)
    except queue.Empty:
        escribir_en_consola("[Abril_SIM]", "Esperando SN...")
        escribir_en_consola_USER("[Abril_SIM]", "Esperando SN...")

    #principal
    while activador:
        try:
            try:
                new_sn = sn_queue.get_nowait()
            except queue.Empty:
                new_sn = None
            if new_sn is not None:
                procesar_sn(new_sn)

            n = Ventrada.in_waiting
            if not n:
                time.sleep(0.003)
                continue

            chunk = Ventrada.read(n)
            if not chunk:
                time.sleep(0.003)
                continue

            buf.extend(chunk)
            while True:
                pos = buf.find(TERM_PC)
                if pos == -1:
                    break
                frame = bytes(buf[:pos + len(TERM_PC)])
                del buf[:pos + len(TERM_PC)]
                texto = frame.decode('utf-8', errors='ignore').strip()
                #escribir_en_consola("[PC->ABRIL-SIM]", f"{texto!r}")
                if texto in dejarPasar:# pasa siempre
                    try:
                        PLC_salida.write(frame)
                        #escribir_en_consola("[ABRIL-SIM]-->PLC", f"{texto!r} (whitelist)")
                    except Exception as e:
                        Controller_Error.Logs_Error.CapturarEvento("main.pc2plc", "write.whitelist", str(e))
                else:
                    # fuera depende del SN (semaforo)
                    if permitir_paso_mensajes:
                        try:
                            PLC_salida.write(frame)
                            escribir_en_consola("[ABRIL-SIM->PLC]", f"{texto!r} (green)")
                        except Exception as e:
                            Controller_Error.Logs_Error.CapturarEvento("main.pc2plc", "write.green", str(e))
                    else:
                        cola_pendientes.put(frame)
                        escribir_en_consola("[ABRIL-SIM]", f"HOLD {texto!r} (SN inválido; en cola)")
                # eventos 
                if texto == "3oe.":
                    iniciar_secuencia = True
                    escribir_en_consola("APP", "Secuencia iniciada (3oe.)")
                elif texto == "10oe.":  
                    resultado_secuencia = "FAIL"
                    escribir_en_consola("APP", "Resultado secuencia = FAIL (10oe.)")
                elif texto == "12oe.":  
                    resultado_secuencia = "PASS"
                    escribir_en_consola("APP", "Resultado secuencia = PASS (12oe.)")
                if resultado_secuencia in ("PASS", "FAIL") and sn_actual:
                    try:
                        ok_bcmp, bcmp_msg, bcmp_resp = CS.Consultas_SIM._check_bcmp(sn_actual, resultado_secuencia)
                    except Exception as e:
                        Controller_Error.Logs_Error.CapturarEvento("main.pc2plc", "check_bcmp", str(e))
                        ok_bcmp, bcmp_msg, bcmp_resp = False, f"BCMP(ERROR_BUILD)|id={sn_actual}|status={resultado_secuencia}", f"ERROR:{e}"

                    # Agregar líneas al buffer
                    _append_log(sn_actual, bcmp_msg)
                    _append_log(sn_actual, bcmp_resp)

                    # Guardar archivo según resultado (PASS/FAIL del proceso) – puedes ajustar esta lógica si querés usar ok_bcmp también
                    try:
                        ruta = logger.save(sn_actual, lineas_log, is_pass=(resultado_secuencia == "PASS" and ok_bcmp))
                        escribir_en_consola("LOG", f"Guardado: {ruta}")
                    except Exception as e:
                        Controller_Error.Logs_Error.CapturarEvento("main.log", "save", str(e))

                    if ok_bcmp:
                        try:
                            PLC_salida.write(b'rs.' + TERM_PC)
                            escribir_en_consola("[ABRIL-SIM->PLC]", "rs. (BCMP OK)")
                        except Exception as e:
                            Controller_Error.Logs_Error.CapturarEvento("main.pc2plc", "write.rs", str(e))
                        reiniciar_ciclo()
                        escribir_en_consola("APP", "Ciclo reiniciado. Ingresá el próximo SN cuando quieras.")
                    else:
                        escribir_en_consola("APP", f"BCMP rechazado para SN [{sn_actual}] con {resultado_secuencia}.")
                        reiniciar_ciclo()
        except Exception as e:
            Controller_Error.Logs_Error.CapturarEvento("main.pc2plc", "loop.error", str(e))
            time.sleep(0.02)
             
        
    





    

















