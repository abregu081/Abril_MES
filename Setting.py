import os
import sys
import Controller_Error

class Setting:
    def __init__(self):
        self.VPORTIN = None
        self.VPORTOUT = None
        self.BAUDRATE = None  
        self.n_char = None
        self.Debug = None

    @staticmethod
    def Capturar_datos_plc(archivo):
        try:
            path_programa = os.path.dirname(os.path.abspath(sys.argv[0]))
            ruta_archivo = os.path.join(path_programa, archivo)
            return ruta_archivo
        except Exception as NoSePudoLeer:
            Controller_Error.Logs_Error.CapturarEvento(
                "CapturarComandosPLC", "CapturarComandosPLC", str(NoSePudoLeer)
            )
            return None
    @staticmethod
    def Capturar_datos_setting(archivo):
        try:
            path_programa = os.path.dirname(os.path.abspath(sys.argv[0]))
            ruta_archivo = os.path.join(path_programa, archivo)
            with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
                archivo_txt = archivo.readlines()
                archivo_txt = [linea.strip() for linea in archivo_txt]
            return archivo_txt
        except Exception as NoSePudoLeer:
            Controller_Error.Logs_Error.CapturarEvento(
                "CapturarDatosSetting", "Capturar_datos_setting", str(NoSePudoLeer)
            )
            return None

    @staticmethod
    def Capturar_datos_setting_MES(archivo):
        try:
            path_programa = os.path.dirname(os.path.abspath(sys.argv[0]))
            ruta_archivo = os.path.join(path_programa, archivo)
            return ruta_archivo
        except Exception as NoSePudoLeer:
            Controller_Error.Logs_Error.CapturarEvento(
                "CapturarSettingMES", "CapturarSettingMES", str(NoSePudoLeer)
            )
            return None

    @staticmethod
    def obtener_parametros_MES():
        setting = {}
        file = Setting.Capturar_datos_setting_MES("MES_settings.ini")
        with open(file, 'r') as f:
            for line in f:
                if(not line or '=' not in line): continue
                if(line[0]=="#"): continue
                key, value = line.split('=', 1)
                if key and value:
                    setting[key.strip()] = value.strip()
        return setting
    
    @staticmethod
    def obtener_Comandos_PLC():
        setting = {}
        file = Setting.Capturar_datos_setting_MES("Comandos_PLC.ini")
        with open(file, 'r') as f:
            for line in f:
                if(not line or '=' not in line): continue
                if(line[0]=="#"): continue
                key, value = line.split('=', 1)
                if key and value:
                    setting[key.strip()] = value.strip()
        return setting
    
    @staticmethod
    def obtener_puertos_comunicaciones():
          #Me devuelve este tipo de lista =  [[ "VPORTIN: COM37", "VPORTOUT: COM38", "n_char: 15" ], ...]
        try:
            archivo_txt = Setting.Capturar_datos_setting("setting.ini")
            if archivo_txt is None:
                return [], None
            sections_list = []
            current_section = []
            debug_val = None
            for raw in archivo_txt:
                line = raw.strip()
                if not line or line.startswith('//'):
                    continue
                if line.lower().startswith('debug:'):
                    try:
                        _, v = line.split(':', 1)
                        debug_val = v.strip()
                    except Exception:
                        pass
                    continue
                if line.startswith('#'):
                    if current_section:
                        sections_list.append(current_section)
                        current_section = []
                    continue
                if ':' in line:
                    key, val = line.split(':', 1)
                    entry = f"{key.strip()}: {val.strip()}"
                    current_section.append(entry)
                    continue

            if current_section:
                sections_list.append(current_section)

            return sections_list, debug_val

        except Exception as e:
            Controller_Error.Logs_Error.CapturarEvento(
                "CapturarDatosSetting", "obtener_puertos_comunicaciones", str(e)
            )
            return [], None