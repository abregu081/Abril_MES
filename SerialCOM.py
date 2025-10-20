import serial
import threading
import Setting as ST
import Controller_Error
from datetime import datetime
import queue
import Consultas_SIM as SIM

class MonitorSerial:
    def __init__(self, VPORTIN, VPORTOUT, baudrate, timeout=None):
        # COM32: Entrada desde TEXAS (virtual)
        self.Ventrada = serial.Serial(VPORTIN, baudrate, timeout=timeout)
        # COM40: Salida hacia PLC físico
        self.PLC_salida = serial.Serial(VPORTOUT, baudrate, timeout=timeout)
        self._activo = False
        self._hilo_pc2plc = None
        self._hilo_plc2pc = None
        self.mensajes_recibidos = []
        self.pc_comandos = queue.Queue(maxsize=200)
        self.debug = "OFF"
        self.estado_mes = False
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
        print("---------INICIANDO MODO SIN MES-------")
        print("TEXiS(COM2) ⇄ COM32 ⇄ APP ⇄ COM40 ⇄ PLC")
        self._activo = True
        self._hilo_pc2plc = threading.Thread(target=self._loop_pc2plc, daemon=True)
        self._hilo_plc2pc = threading.Thread(target=self._loop_plc2pc, daemon=True)
        self._hilo_pc2plc.start()
        self._hilo_plc2pc.start()

    # TEXAS → COM32 → APP → COM40 → PLC
    def _loop_pc2plc(self):
        buf = bytearray()
        TERM_PC = b'\r'
        while self._activo:
            try:
                n = self.Ventrada.in_waiting
                if n:
                    chunk = self.Ventrada.read(n)
                    buf.extend(chunk)
                    while True:
                        pos = buf.find(TERM_PC)
                        if pos == -1:
                            break
                        frame = bytes(buf[:pos+1])
                        del buf[:pos+1]
                        texto = frame.decode('utf-8', errors="ignore").strip()
                        self._log("TEXAS>APP", f"RX {texto!r}")
                        self.PLC_salida.write(frame)
                        #self._log("APP>PLC", f"TX {texto!r}") para ver que le esta enviando la app a mi programa
            except Exception as e:
                print(e)
                #Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "_loop_pc2plc", str(e))
    

    # PLC → COM40 → APP → COM32 → TEXAS
    def _loop_plc2pc(self):
        buf = bytearray()
        TERM_PLC = b'\r'
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
                            self.Ventrada.write(frame)
                            #self._log("APP>TEXAS", f"TX {texto!r}") #Camino inverso del plc a texis
                        except Exception as e:
                            print(e)
                            #Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "plc2pc.write", str(e))
            except Exception as e:
                print(e)
                #Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "_loop_plc2pc", str(e))



    def detener(self):
        self._activo = False
        if self._hilo_pc2plc:
            self._hilo_pc2plc.join(timeout=1.5)
        if self._hilo_plc2pc:
            self._hilo_plc2pc.join(timeout=1.5)
        for sp, name in ((self.Ventrada,"Ventrada"), (self.PLC_salida,"PLC_salida")):
            try:
                if sp and sp.is_open:
                    sp.close()
            except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", f"detener.{name}.close", str(e))