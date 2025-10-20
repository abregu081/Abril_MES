import Conexiones_MES as MES
import Controller_Error
import Setting as ST

class Consultas_SIM:
    def __init__(self, lectura):
        parametros = ST.Setting.obtener_parametros_MES()
        self.ip = parametros['ip']
        self.port = parametros['port']
        self.timeout = int(parametros['timeout_mes'])
        self.proceso = parametros['process']
        self.estacion = parametros['station']
        self.mensajeKey = parametros['mensajeKey']
        self.sn = lectura

    #formato mensajes que le envio a SIM :D
    def _formato_breq(self, sn):
        mensaje = f"BREQ|process={self.proceso}|station={self.estacion}|id={sn}|msgT={self.mensajeKey}" 
        return mensaje

    def _formato_bcmp(self, sn, estado):     
        mensaje = f"BCMP|process={self.proceso}|station={self.estacion}|id={sn}|status={estado}|msgT={self.mensajeKey}"
        return mensaje

    #Con esto le envio el breq a SIM
    def _breq_sn(self, sn):
        breq = self._formato_breq(sn)
        try:
            resp = MES.MES_Socket.enviar_mensaje(self.ip, self.port,self.timeout, breq)
        except TimeoutError as e:
            print("TimeoutError: No se pudo conectar con SIM")
            Controller_Error.Logs_Error.CapturarEvento("ConsultaSIM", "breq_sn", str(e))
            return False
        ok = self._breq_ok(resp)
        # DEVUELVE tupla para log
        return ok, breq, resp
    #envio el bcmp a SIM

    def _bcmp_sn(self, sn):
        bcmp = self._formato_bcmp(sn)
        try:
            resp = MES.MES_Socket.enviar_mensaje(self.ip, self.port,self.timeout, bcmp)
        except TimeoutError as e:
            print("TimeoutError: No se pudo conectar con SIM")
            Controller_Error.Logs_Error.CapturarEvento("Escaner", "bcmp_sn", str(e))

        ok = self._back_ok(resp)
        # DEVUELVE tupla para log
        return ok, bcmp, resp

    
    # ─────────────────────  Se ejecuta directamente Breq y el Bcmp  ─────────────────────────

    def _check_sn(self):
        sn = self.sn.strip()
        if len(sn) != 25:
            return self._breq_sn(sn)


    def _check_bcmp(self,estado):
        sn = self.sn.strip()
        if len(sn) != 25:
            return self._bcmp_sn(sn, estado)
        

    # ─────────────────────  VALIDADORES SIM  ─────────────────────────
    @staticmethod
    def _breq_ok(resp):   # BCNF PASS
        return resp.startswith("BCNF") and "status=PASS" in resp.split('|')[2]

    @staticmethod
    def _back_ok(resp):   # BACK PASS
        return resp.startswith("BACK") and "status=PASS" in resp.split('|')[2]
    
    