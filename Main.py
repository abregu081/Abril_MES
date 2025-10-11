import Controller_Error
import Setting as ST
import time
import SerialCOM as SC_SIN_SIM


configuracion, _ = ST.Setting.obtener_puertos_comunicaciones()
configuracion_MES = ST.Setting.obtener_parametros_MES()


#estado mes
Activador_MES = configuracion_MES["habilitar_mes"]
if Activador_MES == "ON":
    Activador_MES = True
else:
    Activador_MES = False

#Para Funcion sin mes
def crear_monitores(lista_configuraciones):
    monitores = []
    for idx, config in enumerate(lista_configuraciones):
        try:
            # Extraer baudrate, VPORTIN y VPORTOUT de la configuración
            com_baudrate = config[0].split(":")[1].strip()
            com_in = config[1].split(":")[1].strip()
            com_out = config[2].split(":")[1].strip()
            # crear monitor con COM32 (entrada) y COM40 (salida)
            monitor = SC_SIN_SIM.MonitorSerial(com_in, com_out, com_baudrate, timeout=1)
            monitores.append(monitor)
        except Exception as e:
            print(f"Error al crear monitor para configuración {config}: {e}")
            Controller_Error.Logs_Error.CapturarEvento("CrearMonitores", f"Configuracion_{idx+1}", str(e))
    return monitores


#Funcion para el modo con MES
def obtener_parametros_puertos(lista_configuraciones):
    for idx, config in enumerate(lista_configuraciones):
        try:
            com_baudrate = config[0].split(":")[1].strip()
            com_in = config[1].split(":")[1].strip()
            com_out = config[2].split(":")[1].strip()
            return com_baudrate, com_in, com_out
        except Exception as e:
            print(f"Error al crear monitor para configuración {config}: {e}")
            Controller_Error.Logs_Error.CapturarEvento("Obtener_parametros_main", f"Configuracion_{idx+1}", str(e))

print("Abril-SIM | Testing |\n")
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





