import Controller_Error
import Setting as ST
import time
import SerialCOM as SC

# Obtener configuraciones desde setting.ini
configuracion, _ = ST.Setting.obtener_puertos_comunicaciones()

def crear_monitores(lista_configuraciones):
    monitores = []
    for idx, config in enumerate(lista_configuraciones):
        try:
            # Extraer VPORTIN y VPORTOUT de la configuración
            com_in = config[1].split(":")[1].strip()
            com_out = config[2].split(":")[1].strip()
            # Crear monitor con COM32 (entrada) y COM40 (salida)
            monitor = SC.MonitorSerial(com_in, com_out, baudrate=38400, timeout=1)
            monitores.append(monitor)
        except Exception as e:
            print(f"Error al crear monitor para configuración {config}: {e}")
            Controller_Error.Logs_Error.CapturarEvento("CrearMonitores", f"Configuracion_{idx+1}", str(e))
    return monitores

# Crear monitores
puertos_com = crear_monitores(configuracion)

# Mensaje de inicio
print("""
                                                             @@@    
                                                             @@@    
                                                        @@@@@@@@@@@@
@@@         @@@  @@@                                    @@@@@  @@@@@
@@@@       @@@@@ @@@                                         @@@    
@@@@@     @@@@@@      @@@@@   @@@@@@@@    @@@@@    @@@@@@    @@@    
@@@@@@   @@@ @@@ @@@  @@@@@ @@@@  @@@@  @@@   @@@  @@@@@@         
@@ @@@   @@@ @@@ @@@  @@   @@@     @@@ @@@     @@@ @@@              
@@  @@@ @@@  @@@ @@@  @@   @@@      @@ @@@      @@ @@@              
@@  @@@@@@   @@@ @@@  @@    @@@    @@@ @@@@    @@@ @@@              
@@   @@@@@   @@@ @@@  @@     @@@@@@@@@   @@@@@@@@  @@@   - Testing UNAE2    
                                    @@                              
                               @@@@@@@                              
""")
print(f"\nMonitores creados: {len(puertos_com)}")

# Iniciar monitores
for monitor in puertos_com:
    monitor.iniciar()

# Mantener el proceso activo
try:
    while True:
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\n[Debug] Deteniendo el programa manualmente...")
    for monitor in puertos_com:
        monitor.detener()