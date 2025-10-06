import datetime
import os
from socket import gethostbyname, gethostname
import sys

class Logs_Error:   
    @staticmethod
    def CapturarEvento(_aplicativoTraductor, _clase, _evento):
        formatoFechaHorastandar = '%d_%m_%y_%H_%M_%S_%f'
        _fechaactual = datetime.datetime.now().strftime(formatoFechaHorastandar)
        Logs_Error.CrearInfoLogNuevo(_aplicativoTraductor, _fechaactual, _clase, _evento)
        return True
    
    @staticmethod
    def CrearDirectorio(_aplictivonombre):
        absolutoPath = os.path.dirname(os.path.abspath(sys.argv[0]))
        _rutanueva = 'ErrorAplicativo'
        relativoPath = os.path.join(_rutanueva, _aplictivonombre)
        fullPath = os.path.join(absolutoPath, relativoPath)
        if not os.path.exists(fullPath):
            os.makedirs(fullPath)
        return fullPath

    # Metodo 3: Diseño de log ingresando el contenido dentro y titulo
    @staticmethod
    def CrearInfoLogNuevo(_aplicativoTraductor, _fechaactual, _clase, _evento):
        _rutanueva = Logs_Error.CrearDirectorio(_aplicativoTraductor +"\\"+ gethostname())
        log_file_path = os.path.join(_rutanueva, f"{_fechaactual}_{_clase}.txt")
        with open(log_file_path, "w") as file:
            file.write(f"Log de Evento errores - {_aplicativoTraductor}\n")
            file.write(str(_evento))

'''''
#######################################################################################################
# Para realizar prueba de funcionalidad - QA TESTER Manual - usar triple comillas doble para comentar inicio y fin bucle
#######################################################################################################
if __name__ == "__main__":
    logger = Logs_Error()
    aplicativo = "MiAplicativo"
    clase = "MiClase"
    evento = "Este es un mensaje de error."
    logger.CapturarEvento(aplicativo, clase, evento)
'''
