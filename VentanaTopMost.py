#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
VentanaTopMost.py - Mantiene ventanas específicas siempre al frente (Always on Top)
"""

import win32gui
import win32con
import time
import threading
from typing import List, Optional


class VentanaTopMost:
    """
    Clase para mantener ventanas específicas siempre al frente (topmost)
    
    Uso:
        # Mantener una ventana específica al frente
        topmost = VentanaTopMost(titulos=["ERROR", "Abril SIM"])
        topmost.iniciar()
        
        # Detener
        topmost.detener()
    """
    
    def __init__(self, titulos: List[str], intervalo: float = 1.0):
        """
        Inicializa el gestor de ventanas topmost
        
        Args:
            titulos: Lista de títulos de ventanas a mantener al frente (parcial o completo)
            intervalo: Intervalo en segundos para revisar las ventanas (default: 1.0)
        """
        self.titulos = titulos
        self.intervalo = intervalo
        self.activo = False
        self.hilo = None
        
    def encontrar_ventana_por_titulo(self, titulo_parcial: str) -> Optional[int]:
        """
        Encuentra el handle (HWND) de una ventana por título parcial
        
        Args:
            titulo_parcial: Parte del título de la ventana a buscar
            
        Returns:
            HWND de la ventana encontrada o None
        """
        def callback(hwnd, resultado):
            if win32gui.IsWindowVisible(hwnd):
                titulo_ventana = win32gui.GetWindowText(hwnd)
                if titulo_parcial.lower() in titulo_ventana.lower():
                    resultado.append(hwnd)
        
        resultado = []
        win32gui.EnumWindows(callback, resultado)
        return resultado[0] if resultado else None
    
    def set_topmost(self, hwnd: int) -> bool:
        """
        Establece una ventana como topmost (siempre al frente)
        
        Args:
            hwnd: Handle de la ventana
            
        Returns:
            True si fue exitoso, False si falló
        """
        try:
            # HWND_TOPMOST = -1 significa "siempre al frente"
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,  # -1
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
            )
            return True
        except Exception as e:
            print(f"Error estableciendo topmost: {e}")
            return False
    
    def remove_topmost(self, hwnd: int) -> bool:
        """
        Remueve el estado topmost de una ventana
        
        Args:
            hwnd: Handle de la ventana
            
        Returns:
            True si fue exitoso, False si falló
        """
        try:
            # HWND_NOTOPMOST = -2 significa "no siempre al frente"
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_NOTOPMOST,  # -2
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
            )
            return True
        except Exception as e:
            print(f"Error removiendo topmost: {e}")
            return False
    
    def _monitorear_ventanas(self):
        """
        Hilo que monitorea y mantiene las ventanas especificadas al frente
        """
        print(f"[VentanaTopMost] Iniciado - Monitoreando títulos: {self.titulos}")
        
        while self.activo:
            try:
                for titulo in self.titulos:
                    hwnd = self.encontrar_ventana_por_titulo(titulo)
                    if hwnd:
                        # Verificar si ya es topmost
                        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                        es_topmost = bool(ex_style & win32con.WS_EX_TOPMOST)
                        
                        if not es_topmost:
                            if self.set_topmost(hwnd):
                                titulo_completo = win32gui.GetWindowText(hwnd)
                                print(f"[VentanaTopMost] ✓ Ventana '{titulo_completo}' establecida como topmost")
                
                time.sleep(self.intervalo)
                
            except Exception as e:
                print(f"[VentanaTopMost] Error en monitoreo: {e}")
                time.sleep(self.intervalo)
        
        print("[VentanaTopMost] Monitoreo detenido")
    
    def iniciar(self):
        """
        Inicia el monitoreo de ventanas en segundo plano
        """
        if not self.activo:
            self.activo = True
            self.hilo = threading.Thread(target=self._monitorear_ventanas, daemon=True, name="VentanaTopMost")
            self.hilo.start()
            print("[VentanaTopMost] Iniciado correctamente")
    
    def detener(self):
        """
        Detiene el monitoreo de ventanas
        """
        if self.activo:
            self.activo = False
            if self.hilo:
                self.hilo.join(timeout=2)
            print("[VentanaTopMost] Detenido correctamente")
    
    def set_ventana_topmost_ahora(self, titulo: str) -> bool:
        """
        Establece una ventana como topmost inmediatamente (sin monitoreo continuo)
        
        Args:
            titulo: Título (parcial o completo) de la ventana
            
        Returns:
            True si fue exitoso, False si falló
        """
        hwnd = self.encontrar_ventana_por_titulo(titulo)
        if hwnd:
            return self.set_topmost(hwnd)
        return False


class VentanaTkinterTopMost:
    """
    Clase específica para ventanas tkinter
    Más simple y directo
    """
    
    @staticmethod
    def set_topmost(ventana_tk):
        """
        Establece una ventana tkinter como topmost
        
        Args:
            ventana_tk: Instancia de tk.Tk() o tk.Toplevel()
            
        Ejemplo:
            root = tk.Tk()
            VentanaTkinterTopMost.set_topmost(root)
        """
        ventana_tk.attributes('-topmost', True)
        ventana_tk.update()
    
    @staticmethod
    def remove_topmost(ventana_tk):
        """
        Remueve el topmost de una ventana tkinter
        
        Args:
            ventana_tk: Instancia de tk.Tk() o tk.Toplevel()
        """
        ventana_tk.attributes('-topmost', False)
        ventana_tk.update()
    
    @staticmethod
    def toggle_topmost(ventana_tk):
        """
        Alterna el estado topmost de una ventana tkinter
        
        Args:
            ventana_tk: Instancia de tk.Tk() o tk.Toplevel()
            
        Returns:
            True si ahora es topmost, False si no
        """
        estado_actual = ventana_tk.attributes('-topmost')
        nuevo_estado = not estado_actual
        ventana_tk.attributes('-topmost', nuevo_estado)
        ventana_tk.update()
        return nuevo_estado


# ===== EJEMPLO DE USO =====

if __name__ == "__main__":
    import tkinter as tk
    
    print("=== DEMO VentanaTopMost ===\n")
    
    # Ejemplo 1: Mantener ventanas de error siempre al frente
    print("Ejemplo 1: Monitoreo automático de ventanas")
    topmost = VentanaTopMost(
        titulos=["ERROR", "Error", "Abril SIM", "TIMEOUT"],
        intervalo=0.5  # Revisar cada 500ms
    )
    topmost.iniciar()
    
    # Ejemplo 2: Ventana tkinter con botón para toggle topmost
    print("\nEjemplo 2: Ventana tkinter con control manual\n")
    
    root = tk.Tk()
    root.title("Demo TopMost")
    root.geometry("400x300")
    
    # Estado inicial
    es_topmost = False
    
    def toggle():
        global es_topmost
        es_topmost = VentanaTkinterTopMost.toggle_topmost(root)
        estado = "ACTIVO ✓" if es_topmost else "INACTIVO"
        btn_toggle.config(text=f"TopMost: {estado}")
        lbl_estado.config(
            text=f"Ventana {'siempre al frente' if es_topmost else 'normal'}",
            fg="green" if es_topmost else "gray"
        )
    
    # Interfaz
    tk.Label(root, text="Control de Ventana TopMost", 
            font=("Arial", 16, "bold")).pack(pady=20)
    
    lbl_estado = tk.Label(root, text="Ventana normal", 
                         font=("Arial", 12), fg="gray")
    lbl_estado.pack(pady=10)
    
    btn_toggle = tk.Button(root, text="TopMost: INACTIVO", 
                          command=toggle,
                          font=("Arial", 12, "bold"),
                          bg="#3498db", fg="white",
                          width=20, height=2)
    btn_toggle.pack(pady=20)
    
    tk.Label(root, text="Presiona el botón para activar/desactivar\nla ventana siempre al frente",
            font=("Arial", 9), fg="gray").pack(pady=10)
    
    # Botón para crear ventana de prueba
    def crear_ventana_prueba():
        ventana_prueba = tk.Toplevel(root)
        ventana_prueba.title("Ventana de Prueba")
        ventana_prueba.geometry("300x200")
        
        tk.Label(ventana_prueba, text="Esta es una ventana de prueba",
                font=("Arial", 11)).pack(pady=20)
        
        tk.Button(ventana_prueba, text="Hacer TopMost",
                 command=lambda: VentanaTkinterTopMost.set_topmost(ventana_prueba),
                 bg="#27ae60", fg="white").pack(pady=5)
        
        tk.Button(ventana_prueba, text="Quitar TopMost",
                 command=lambda: VentanaTkinterTopMost.remove_topmost(ventana_prueba),
                 bg="#e74c3c", fg="white").pack(pady=5)
    
    tk.Button(root, text="Crear Ventana de Prueba",
             command=crear_ventana_prueba,
             bg="#95a5a6", fg="white").pack(pady=10)
    
    # Al cerrar, detener el monitoreo
    def on_closing():
        topmost.detener()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    print("Ventana demo iniciada. Cierra la ventana para terminar.")
    root.mainloop()
