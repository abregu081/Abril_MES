import serial
import threading
import Setting as ST
import Controller_Error
from datetime import datetime
import queue
import Consultas_SIM as SIM

class MonitorSerial_con_SIM:
    def __init__(self, VPORTIN, VPORTOUT, baudrate, timeout=1):
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
        self.valores_definidos_taxis = ["16in", "ec", "0in"]
        self.sn_validacion = False      # SN validado
        self.iniciar_secuencia = False  # Secuencia iniciada cuando se reciba "3oe"
        self.resultado_secuncia = None    # "FAIL" o "PASS"
        self.sn = None               #SN leido por el usuario
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
        print("---------INICIANDO MODO CON MES-------")
        print("TEXiS(COM2) ⇄ COM32 ⇄ ABRIL-SIM ⇄ COM40 ⇄ PLC")
        self._activo = True
        self._hilo_pc2plc = threading.Thread(target=self._loop_pc2plc_MES, daemon=True)
        self._hilo_plc2pc = threading.Thread(target=self._loop_plc2pc_MES, daemon=True)
        self._hilo_pc2plc.start()
        self._hilo_plc2pc.start()

    # TEXAS → COM32 → APP → COM40 → PLC
    def _loop_pc2plc_MES(self):
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

                        #self._log("TEXAS--->Abril_SIM", f"RX {texto!r}")

                        if texto == "3oe":
                            self.sequence_started = True
                            self._log("SEQUENCE", "Secuencia iniciada (3oe)")
                            
            except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "_loop_pc2plc", str(e))
    
    # PLC → COM40 → APP → COM32 → TEXAS
    def _loop_plc2pc_MES(self):
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
                        except Exception as e:
                            Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "plc2pc.write", str(e))
            except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "_loop_plc2pc", str(e))

    def escribir_a_plc(self, mensaje: str):
        try:
            self.PLC_salida.write((mensaje + "\n").encode('utf-8'))
            self._log("APP>PLC", f"TX {mensaje!r}")
        except Exception as e:
            Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "escribir_a_plc", str(e))

    def poka_yoke(self, texto):
        # Permitir siempre los mensajes iniciales para iniciar el programa.
        if texto in self.valores_definidos_taxis:
            return True

        # Si aún no se ha validado el SN, se bloquean otros mensajes.
        if not self.sn_validacion:
            return False

        # A partir de aquí, se dejan pasar todos los mensajes y se verifica la secuencia.
        if texto == "3oe":
            self.sequence_started = True
            self._log("SEQUENCE", "Secuencia iniciada (3oe)")
        if self.sequence_started:
            if texto in ("10oe", "11oe"):
                self.sequence_result = "FAIL"
                self._log("SEQUENCE", f"Secuencia finalizada con fallo ({texto})")
                self.finalizar_secuencia()
            elif texto in ("12oe", "13oe"):
                self.sequence_result = "PASS"
                self._log("SEQUENCE", f"Secuencia finalizada con éxito ({texto})")
                self.finalizar_secuencia()
        return True

    def finalizar_secuencia(self):
        # Se llama al método _check_bcmp de Consultas_SIM para enviar el resultado final.
        try:
            sim = SIM.Consultas_SIM(self.sn)  # Se asume que el constructor recibe el sn leído
            # Se envía el bcmp con el estado obtenido (por ejemplo, "FAIL" o "PASS")
            sim._check_bcmp(self.sn, self.sequence_result)
        except Exception as e:
            Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "finalize_sequence", str(e))
    
    # Método para solicitar y validar el SN introducido por el usuario.
    def set_sn(self, sn):
        self.sn = sn.strip()
        try:
            sim = SIM.Consultas_SIM(self.sn)
            result = sim._check_sn(self.sn)
            if result:
                self.sn_validated = True
                self._log("SN", f"SN {self.sn} validado correctamente")
            else:
                self._log("SN", f"SN {self.sn} no es válido")
            return result
        except Exception as e:
            Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", "set_sn", str(e))
            return False

    def detener(self):
        self._activo = False
        if self._hilo_pc2plc:
            self._hilo_pc2plc.join(timeout=1.5)
        if self._hilo_plc2pc:
            self._hilo_plc2pc.join(timeout=1.5)
        for sp, name in ((self.Ventrada, "Ventrada"), (self.PLC_salida, "PLC_salida")):
            try:
                if sp and sp.is_open:
                    sp.close()
            except Exception as e:
                Controller_Error.Logs_Error.CapturarEvento("MonitorSerial", f"detener.{name}.close", str(e))