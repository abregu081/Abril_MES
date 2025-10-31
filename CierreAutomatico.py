"""
CierreAutomatico.py
Clase para cerrar ventanas automáticamente usando PyAutoGUI
Autor: Abregu Tomas
Fecha: 2025
"""

import pyautogui
import time
import threading
from typing import Optional, List
import win32gui
import win32con


class CerrarVentanaAutomatica:
    """
    Clase para detectar y cerrar ventanas automáticamente haciendo clic en botones específicos.
    Usa PyAutoGUI y Win32 API para máxima compatibilidad.
    """
    
    def __init__(self, titulos_ventanas: List[str] = None, texto_boton: str = "OK", intervalo: float = 1.0):
        """
        Inicializa el auto-closer.
        
        Args:
            titulos_ventanas: Lista de títulos de ventanas a cerrar (por defecto ["ERROR"])
            texto_boton: Texto del botón a buscar (por defecto "OK")
            intervalo: Intervalo de tiempo entre búsquedas en segundos (por defecto 1.0)
        """
        self.titulos_ventanas = titulos_ventanas or ["ERROR", "Error", "error"]
        self.texto_boton = texto_boton
        self.intervalo = intervalo
        self.activo = False
        self.hilo = None
        self.ventanas_cerradas = 0
        self.log_callback = None  # Callback para logging externo
        
    def set_log_callback(self, callback):
        """
        Establece una función de callback para logging.
        
        Args:
            callback: Función que recibe (tag, mensaje)
        """
        self.log_callback = callback
    
    def _log(self, tag: str, mensaje: str):
        """Log interno"""
        if self.log_callback:
            self.log_callback(tag, mensaje)
        else:
            print(f"[{tag}] {mensaje}")
    
    def iniciar(self):
        """Inicia el monitoreo de ventanas en un hilo separado"""
        self.activo = True
        self.hilo = threading.Thread(target=self._monitorear_ventanas, daemon=True, name="AutoCloserThread")
        self.hilo.start()
        self._log("AutoCloser", f"✓ Iniciado - Monitoreando ventanas: {', '.join(self.titulos_ventanas)}")
    
    def detener(self):
        """Detiene el monitoreo de ventanas"""
        if not self.activo:
            return
        
        self.activo = False
        if self.hilo:
            self.hilo.join(timeout=2)
        self._log("AutoCloser", f"✓ Detenido - Ventanas cerradas en total: {self.ventanas_cerradas}")
    
    def _monitorear_ventanas(self):
        """Hilo principal que monitorea y cierra ventanas"""
        while self.activo:
            try:
                self._buscar_y_cerrar_ventanas()
                time.sleep(self.intervalo)
            except Exception as e:
                self._log("ERROR", f"Error en monitoreo: {e}")
                time.sleep(2)
    
    def _buscar_y_cerrar_ventanas(self):
        """Busca ventanas por título y las cierra"""
        def callback(hwnd, extra):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                
                titulo = win32gui.GetWindowText(hwnd)
                
                # Verificar si el título coincide con alguno de la lista
                for titulo_objetivo in self.titulos_ventanas:
                    if titulo_objetivo.lower() in titulo.lower():
                        self._log("AutoCloser", f"⚠ Ventana detectada: '{titulo}'")
                        
                        # Traer ventana al frente
                        win32gui.SetForegroundWindow(hwnd)
                        time.sleep(0.2)
                        
                        # Intentar hacer clic en el botón
                        if self._click_boton_en_ventana(hwnd):
                            self.ventanas_cerradas += 1
                            self._log("AutoCloser", f"✓ Ventana cerrada exitosamente (botón '{self.texto_boton}')")
                        else:
                            # Si no encuentra botón, intentar cerrar con Alt+F4 o Enter
                            self._cerrar_ventana_alternativo(hwnd, titulo)
                        
                        break
                        
            except Exception as e:
                self._log("ERROR", f"Error procesando ventana: {e}")
            
            return True
        
        try:
            win32gui.EnumWindows(callback, None)
        except Exception as e:
            self._log("ERROR", f"Error enumerando ventanas: {e}")
    
    def _click_boton_en_ventana(self, hwnd_ventana) -> bool:
        """
        Busca y hace clic en un botón dentro de una ventana.
        
        Args:
            hwnd_ventana: Handle de la ventana
            
        Returns:
            True si encontró y clickeó el botón, False en caso contrario
        """
        try:
            # Método 1: Buscar botón por texto usando Win32 API
            def callback_boton(hwnd, botones):
                try:
                    texto = win32gui.GetWindowText(hwnd)
                    clase = win32gui.GetClassName(hwnd)
                    
                    # Verificar si es un botón y tiene el texto correcto
                    if "BUTTON" in clase.upper():
                        if texto.upper() == self.texto_boton.upper() or \
                           self.texto_boton.upper() in texto.upper():
                            botones.append(hwnd)
                            self._log("AutoCloser", f"  → Botón encontrado: '{texto}'")
                except:
                    pass
                return True
            
            botones = []
            win32gui.EnumChildWindows(hwnd_ventana, callback_boton, botones)
            
            if botones:
                # Hacer clic en el botón usando Win32
                win32gui.SendMessage(botones[0], win32con.BM_CLICK, 0, 0)
                time.sleep(0.1)
                return True
            
            # Método 2: Si no encuentra el botón, intentar con PyAutoGUI presionando Enter
            self._log("AutoCloser", f"  → Botón '{self.texto_boton}' no encontrado, intentando Enter...")
            pyautogui.press('enter')
            time.sleep(0.1)
            return True
            
        except Exception as e:
            self._log("ERROR", f"Error haciendo clic en botón: {e}")
            return False
    
    def _cerrar_ventana_alternativo(self, hwnd, titulo):
        """Métodos alternativos para cerrar la ventana si no se encuentra el botón"""
        try:
            self._log("AutoCloser", f"  → Intentando método alternativo para cerrar '{titulo}'")
            
            # Método 1: Enviar WM_CLOSE
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            time.sleep(0.1)
            
            # Verificar si se cerró
            if not win32gui.IsWindow(hwnd):
                self.ventanas_cerradas += 1
                self._log("AutoCloser", "  ✓ Ventana cerrada con WM_CLOSE")
                return True
            
            # Método 2: Alt+F4 con PyAutoGUI
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1)
            pyautogui.hotkey('alt', 'f4')
            time.sleep(0.1)
            
            if not win32gui.IsWindow(hwnd):
                self.ventanas_cerradas += 1
                self._log("AutoCloser", "  ✓ Ventana cerrada con Alt+F4")
                return True
            
            # Método 3: Presionar Escape
            pyautogui.press('esc')
            time.sleep(0.1)
            
            if not win32gui.IsWindow(hwnd):
                self.ventanas_cerradas += 1
                self._log("AutoCloser", "  ✓ Ventana cerrada con Escape")
                return True
            
            self._log("AutoCloser", "  ✗ No se pudo cerrar la ventana con métodos alternativos")
            return False
            
        except Exception as e:
            self._log("ERROR", f"Error en método alternativo: {e}")
            return False
    
    def cerrar_ventana_ahora(self, titulo_parcial: str) -> bool:
        """
        Busca y cierra una ventana inmediatamente (sin esperar el intervalo).
        
        Args:
            titulo_parcial: Parte del título de la ventana a cerrar
            
        Returns:
            True si encontró y cerró la ventana, False en caso contrario
        """
        try:
            def callback(hwnd, encontrado):
                try:
                    if win32gui.IsWindowVisible(hwnd):
                        titulo = win32gui.GetWindowText(hwnd)
                        if titulo_parcial.lower() in titulo.lower():
                            encontrado.append(hwnd)
                            return False  # Detener búsqueda
                except:
                    pass
                return True
            
            ventanas_encontradas = []
            win32gui.EnumWindows(callback, ventanas_encontradas)
            
            if ventanas_encontradas:
                hwnd = ventanas_encontradas[0]
                titulo = win32gui.GetWindowText(hwnd)
                self._log("AutoCloser", f"Cerrando ventana manualmente: '{titulo}'")
                
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.2)
                
                if self._click_boton_en_ventana(hwnd):
                    self._log("AutoCloser", "✓ Ventana cerrada exitosamente")
                    return True
                else:
                    return self._cerrar_ventana_alternativo(hwnd, titulo)
            else:
                self._log("AutoCloser", f"No se encontró ventana con título: '{titulo_parcial}'")
                return False
                
        except Exception as e:
            self._log("ERROR", f"Error cerrando ventana manualmente: {e}")
            return False
    
    def obtener_estadisticas(self) -> dict:
        """
        Obtiene estadísticas del auto-closer.
        
        Returns:
            Diccionario con estadísticas
        """
        return {
            "activo": self.activo,
            "ventanas_cerradas": self.ventanas_cerradas,
            "titulos_monitoreados": self.titulos_ventanas,
            "texto_boton": self.texto_boton,
            "intervalo": self.intervalo
        }


# ========================================
# EJEMPLO DE USO
# ========================================

if __name__ == "__main__":
    print("=" * 50)
    print("  TEST: CerrarVentanaAutomatica")
    print("=" * 50)
    print()
    
    # Crear instancia del auto-closer
    auto_closer = CerrarVentanaAutomatica(
        titulos_ventanas=["ERROR", "Error", "Advertencia", "Warning"],
        texto_boton="OK",
        intervalo=1.0
    )
    
    # Iniciar monitoreo
    auto_closer.iniciar()
    
    print("\n✓ Auto-closer activo")
    print("  Monitoreando ventanas con títulos: ERROR, Error, Advertencia, Warning")
    print("  Buscando botón: OK")
    print()
    print("  Presiona Ctrl+C para detener...")
    print()
    
    try:
        # Mantener el programa corriendo
        while True:
            time.sleep(1)
            
            # Mostrar estadísticas cada 10 segundos
            if int(time.time()) % 10 == 0:
                stats = auto_closer.obtener_estadisticas()
                print(f"  [INFO] Ventanas cerradas: {stats['ventanas_cerradas']}")
    
    except KeyboardInterrupt:
        print("\n\n✓ Deteniendo auto-closer...")
        auto_closer.detener()
        
        # Mostrar estadísticas finales
        stats = auto_closer.obtener_estadisticas()
        print()
        print("=" * 50)
        print("  ESTADÍSTICAS FINALES")
        print("=" * 50)
        print(f"  Ventanas cerradas: {stats['ventanas_cerradas']}")
        print(f"  Títulos monitoreados: {', '.join(stats['titulos_monitoreados'])}")
        print(f"  Botón buscado: {stats['texto_boton']}")
        print()


