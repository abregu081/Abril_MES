import socket
import os
import Setting as ST
import Controller_Error

#COMUNICACION SIM - ABRIL :D

class MES_Socket:
    parametros = ST.Setting.obtener_parametros_MES()
    ip = parametros['ip']
    port = parametros['port']
    timeout = int(parametros['timeout_mes'])
    @staticmethod
    def enviar_mensaje(ip, port, timeout ,msg):
        client_socket = None
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(timeout)
            client_socket.connect((ip, int(port)))
            client_socket.sendall((msg + "\n").encode('utf-8'))
            respuesta = client_socket.recv(1024).decode('utf-8').replace("\n", "")
            client_socket.close()
            print(f"\n[SIM]: {respuesta}")
            return respuesta
        except socket.timeout as timeout_error:
            print("\n[ Abril ] Timeout esperando respuesta de SIM")
            if client_socket:
                client_socket.close()
            Controller_Error.Logs_Error.CapturarEvento("MES_Socket", "send_message", str(timeout_error))
            raise TimeoutError(str(timeout_error))
        except Exception as fallo_conexion:
            print("\n[ Abril ] No se pudo conectar con SIM")
            if client_socket:
                client_socket.close()
            Controller_Error.Logs_Error.CapturarEvento("MES_Socket", "send_message", str(fallo_conexion))
            raise Exception(str(fallo_conexion))



