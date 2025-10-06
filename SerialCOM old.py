import serial
import threading
import Setting as ST
import Controller_Error
from datetime import datetime
import queue

class MonitorSerial:
    def __init__(self, FPORTIN, VPORTIN, VPORTOUT, baudrate, timeout=1):
        # COM2 físico PLC
        self.PLC_salida = serial.Serial(FPORTIN, baudrate, timeout=timeout)
        # COM3 puerto virtual texas (PC -> APP)
        self.Ventrada = serial.Serial(VPORTIN, baudrate, timeout=timeout)
        # COM5 puerto virtual para devolver a TEXAS (APP -> PC)
        self.Vsalida = serial.Serial(VPORTOUT, baudrate, timeout=timeout)

        self._activo = False
        self._hilo_pc2plc = None
        self._hilo_plc2pc = None
        self.mensajes_recibidos = []
        self.pc_comandos = queue.Queue(maxsize=200)

        self.debug = "OFF"
        try:
            for linea in ST.Setting.Capturar_datos_setting("setting.ini"):
                if linea.lower().startswith("debug:"):
                    _, val = linea.split(":", 1)
                    self.debug = val.strip().upper()
        except Exception as e:
            Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "__init__.settings", str(e))

    def _log(self, tag, msg):
        if self.debug == "ON":
            print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [{tag}] {msg}")

    def iniciar(self):
        print("Sniffer (3 puertos) activo: PC(COM3)->APP->PLC(COM2) y PLC->APP->PC(COM5)")
        self._activo = True
        self._hilo_pc2plc = threading.Thread(target=self._loop_pc2plc, daemon=True)
        self._hilo_plc2pc = threading.Thread(target=self._loop_plc2pc, daemon=True)
        self._hilo_pc2plc.start()
        self._hilo_plc2pc.start()

     # PC -> APP -> PLC
    def _loop_pc2plc(self):
        buf = bytearray()
        TERM_PC = b'\r' # 0x0D según que vi que enviaba 
        while self._activo:
            try:
                n = self.Ventrada.in_waiting
                if n:
                    chunk = self.Ventrada.read(n)
                    buf.extend(chunk)
                    # reenviar frames completos terminados en CR
                    while True:
                        pos = buf.find(TERM_PC)
                        if pos == -1:
                            break
                        frame = bytes(buf[:pos+1])  # incluye el CR
                        del buf[:pos+1]
                        texto = frame.decode('utf-8', errors="ignore").strip()
                        self._log("PC>APP", f"RX {texto!r}")
                        self.PLC_salida.write(frame)
                        self._log("APP>PLC", f"TX {texto!r}")
            except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "_loop_pc2plc", str(e))

    # PLC -> APP -> PC
    def _loop_plc2pc(self):
        buf = bytearray()
        TERM_PLC = b'\n\r' 
        while self._activo:
            try:
                n = self.PLC_salida.in_waiting
                if n:
                    chunk = self.PLC_salida.read(n)
                    buf.extend(chunk)
                    while True:
                        pos = buf.find(TERM_PLC)
                        if pos == -1:
                            break
                        frame = bytes(buf[:pos+len(TERM_PLC)])
                        del buf[:pos+len(TERM_PLC)]
                        texto = frame.decode('utf-8', errors="ignore").strip()
                        self.mensajes_recibidos.append(texto)
                        self._log("PLC>APP", f"RX {texto!r}")
                        try:
                            self.Vsalida.write(frame)
                            self._log("APP>PC", f"TX {texto!r}")
                        except Exception as e:
                            Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "plc2pc.write", str(e))
            except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "_loop_plc2pc", str(e))
    
    # enviar algo manual al plc
    def escribir_a_pcl(self, mensaje: str):
        try:
            self.PLC_salida.write((mensaje + "\n").encode('utf-8'))
            self._log("APP>PLC", f"TX {mensaje!r}")
        except Exception as e:
            Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "escribir_a_pc", str(e))

    def detener(self):
        self._activo = False
        if self._hilo_pc2plc:
            self._hilo_pc2plc.join(timeout=1.5)
        if self._hilo_plc2pc:
            self._hilo_plc2pc.join(timeout=1.5)
        for sp, name in ((self.PLC_salida,"PLC_salida"), (self.Ventrada,"Ventrada"), (self.Vsalida,"Vsalida")):
            try:
                if sp and sp.is_open:
                    sp.close()
            except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", f"detener.{name}.close", str(e))
