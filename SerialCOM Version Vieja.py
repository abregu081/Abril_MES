import serial
import threading
import Setting as ST
import Controller_Error
from datetime import datetime
import queue

class MonitorSerial:
    
    def __init__(self, FPORTIN, VPORTIN, VPORTOUT, baudrate, timeout=1):
        # puerto conectado al PLC (para leer la respuesta)
        self.PLC_salida = serial.Serial(FPORTIN, baudrate, timeout=timeout)
        # puerto en donde la PC escribe comandos (entrada al sniffer)
        self.Ventrada = serial.Serial(VPORTIN, baudrate, timeout=timeout)
        # puerto para reenviar el mensaje a la PC
        self.Vsalida = serial.Serial(VPORTOUT, baudrate, timeout=timeout)
        self._activo = False
        self._hilo_respuesta_plc = None
        self._hilo_pc_input = None
        self.mensajes_recibidos = []
        self.pc_comandos = queue.Queue()
        self.modo = ST.Setting.Capturar_datos_setting("setting.ini")
        self.debug = "OFF"
        for linea in self.modo:
            if linea.lower().startswith("debug:"):
                try:
                    _, val = linea.split(":", 1)
                    self.debug = val.strip().upper()
                except:
                    pass

    def iniciar(self):
        print("Iniciando el modo sniffer entre Ventrada y Vsalida, y monitoreo de respuesta del PLC")
        self._activo = True
        # Hilo para leer la respuesta del PLC
        self._hilo_respuesta_plc = threading.Thread(target=self.monitor_respuesta_plc)
        self._hilo_respuesta_plc.start()
        # Hilo para leer los comandos que envía la PC en Ventrada y reenviarlos a Vsalida
        self._hilo_pc_input = threading.Thread(target=self.monitor_pc_input)
        self._hilo_pc_input.start()

    # lee los mensajes desde Ventrada (donde la PC escribe)
    def monitor_pc_input(self):
        while self._activo:
            try:
                if self.Ventrada.in_waiting > 0:
                    datos = self.Ventrada.read(self.Ventrada.in_waiting)
                    texto = datos.decode('utf-8', errors="ignore").strip()
                    if self.debug == "ON":
                        print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [Debug - PC] Datos recibidos en Ventrada: {texto}")
                        #print(" ".join(f"{b:02x}" for b in datos), " ", texto)
                    self.pc_comandos.put(texto)
            except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "monitor_pc_input", str(e))

    # Lee la respuesta que viene del PLC y la almacena o la muestra en consola
    def monitor_respuesta_plc(self):
        while self._activo:
            try:
                if self.PLC_salida.in_waiting > 0:
                    datos = self.PLC_salida.read(self.PLC_salida.in_waiting)
                    texto = datos.decode('utf-8', errors="ignore").strip()
                    self.mensajes_recibidos.append(texto)
                    if self.debug == "ON":
                        print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [Debug - PLC] Datos recibidos del PLC (PLC_salida): {texto}")
                        # print(" ".join(f"{b:02x}" for b in datos), " ", texto)
            except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "monitor_respuesta_plc", str(e))

    def Escibir_Mensaje_VPORTIN(self, mensaje):
        try:
            # Se envía directamente el mensaje (en este flujo ya se envían los datos que llegan de Ventrada)
            self.Vsalida.write(mensaje.encode('utf-8'))
            if self.debug == "ON":
                print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [Debug - PC] Comando enviado desde la PC (Vsalida): {mensaje}")
        except Exception as e:
            Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "Escibir_Mensaje_VPORTIN", str(e))
        
    def detener(self):
        self._activo = False
        if self._hilo_respuesta_plc:
            self._hilo_respuesta_plc.join()
        if self._hilo_pc_input:
            self._hilo_pc_input.join()