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
            Mensaje_y_Respuesta_SIM = MES.MES_Socket.enviar_mensaje(self.ip, self.port,self.timeout, breq)
        except TimeoutError as e:
            print("TimeoutError: No se pudo conectar con SIM")
            Controller_Error.Logs_Error.CapturarEvento("Escaner", "breq_sn", str(e))
            return False
        if not self._breq_ok(Mensaje_y_Respuesta_SIM):
            print("\n[SIM] : BREQ status=FAIL")
            return False
        else:
            print("\n[SIM] : BREQ status=PASS") # Despues tengo que agregar la parte del procesamiento
           # Antes de esa parte tiene que ir el objeto para procesar la info del sniffer
            return True
    #envio el bcmp a SIM
    def _bcmp_sn(self, sn):
        bcmp = self._formato_bcmp(sn)
        try:
            resp = MES.MES_Socket.enviar_mensaje(self.ip, self.port,self.timeout, bcmp)
        except TimeoutError as e:
            print("TimeoutError: No se pudo conectar con SIM")
            Controller_Error.Logs_Error.CapturarEvento("Escaner", "bcmp_sn", str(e))

        if self._back_ok(resp):
            print("\n[SIM] : BCMP status=PASS")
        else:
            print("\n[SIM] : BCMP status=FAIL")

    #Con esto el escaner verifica agrupando 
    def _check_sn(self, sn):
        sn = self.sn.strip()
        if len(sn) != 25:
            return self._breq_sn(sn)


    #Ejecuto directamento el  bcmp
    def _check_bcmp(self, sn ,estado):
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
    
    