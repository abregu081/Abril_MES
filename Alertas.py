import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable


class PopUpAvisos:    
    def __init__(self, titulo_app: str = "Sistema MES"):
        self.titulo_app = titulo_app
    

    def timeout(
            self,
            mensaje: str,
            titulo: Optional[str] = None,
            ancho: int = 500,
            alto: int = 300
    ) -> None:
        titulo = titulo or "TIMEOUT"
        
        popup = tk.Toplevel()
        popup.title(titulo)
        popup.geometry(f"{ancho}x{alto}")
        popup.resizable(False, False)
        popup.configure(bg="#000000")  # Fondo rojo claro
        
        # Centrar la ventana
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (ancho // 2)
        y = (popup.winfo_screenheight() // 2) - (alto // 2)
        popup.geometry(f"{ancho}x{alto}+{x}+{y}")
        
        # Hacer la ventana modal
        popup.transient()
        popup.grab_set()
        
        # Frame para el contenido
        frame_contenido = tk.Frame(popup, bg="#000000", padx=20, pady=20)
        frame_contenido.pack(expand=True, fill=tk.BOTH)
        
        # Etiqueta del título con icono
        label_titulo = tk.Label(
            frame_contenido,
            text="TIMEOUT",
            font=("Arial", 20, "bold"),
            fg="#e5ff00",
            bg="#000000"
        )
        label_titulo.pack(pady=(0, 10))
        
        # Etiqueta del mensaje
        label_mensaje = tk.Label(
            frame_contenido, 
            text=mensaje, 
            wraplength=ancho-40,
            justify=tk.CENTER,
            font=("Arial", 11),
            fg="#FFFFFF",
            bg="#000000"
        )
        label_mensaje.pack(expand=True)
        
        # Frame para el botón
        frame_boton = tk.Frame(popup, bg="#000000", pady=10)
        frame_boton.pack()
        
        # Botón Cerrar
        btn_cerrar = tk.Button(
            frame_boton, 
            text="Cerrar", 
            command=popup.destroy,
            width=12,
            bg="#000000",
            fg="white",
            font=("Arial", 10, "bold"),
            relief=tk.RAISED,
            bd=2
        )
        btn_cerrar.pack()
        
        # Enfocar el botón
        btn_cerrar.focus_set()
        
        try:
            popup.bell()
        except:
            pass
        popup.wait_window()

    def fail(
        self, 
        mensaje: str, 
        titulo: Optional[str] = None,
        ancho: int = 500,
        alto: int = 300
    ) -> None:
        titulo = titulo or "FAIL"
        
        popup = tk.Toplevel()
        popup.title(titulo)
        popup.geometry(f"{ancho}x{alto}")
        popup.resizable(False, False)
        popup.configure(bg="#000000")  # Fondo rojo claro
        
        # Centrar la ventana
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (ancho // 2)
        y = (popup.winfo_screenheight() // 2) - (alto // 2)
        popup.geometry(f"{ancho}x{alto}+{x}+{y}")
        
        # Hacer la ventana modal
        popup.transient()
        popup.grab_set()
        
        # Frame para el contenido
        frame_contenido = tk.Frame(popup, bg="#000000", padx=20, pady=20)
        frame_contenido.pack(expand=True, fill=tk.BOTH)
        
        # Etiqueta del título con icono
        label_titulo = tk.Label(
            frame_contenido,
            text="FAIL",
            font=("Arial", 20, "bold"),
            fg="#ff0000",
            bg="#000000"
        )
        label_titulo.pack(pady=(0, 10))
        
        # Etiqueta del mensaje
        label_mensaje = tk.Label(
            frame_contenido, 
            text=mensaje, 
            wraplength=ancho-40,
            justify=tk.CENTER,
            font=("Arial", 11),
            fg="#FFFFFF",
            bg="#000000"
        )
        label_mensaje.pack(expand=True)
        
        # Frame para el botón
        frame_boton = tk.Frame(popup, bg="#000000", pady=10)
        frame_boton.pack()
        
        # Botón Cerrar
        btn_cerrar = tk.Button(
            frame_boton, 
            text="Cerrar", 
            command=popup.destroy,
            width=12,
            bg="#000000",
            fg="white",
            font=("Arial", 10, "bold"),
            relief=tk.RAISED,
            bd=2
        )
        btn_cerrar.pack()
        
        # Enfocar el botón
        btn_cerrar.focus_set()
        
        try:
            popup.bell()
        except:
            pass
        popup.wait_window()
    
    def pass_temporal(
        self, 
        mensaje: str, 
        titulo: Optional[str] = None,
        ancho: int = 400,
        alto: int = 200,
        duracion: int = 3000
    ) -> None:
        """
        Muestra un pop-up de éxito temporal que se cierra automáticamente después de 3 segundos.
        
        Args:
            mensaje: Texto del mensaje a mostrar
            titulo: Título de la ventana (opcional)
            ancho: Ancho de la ventana en píxeles
            alto: Alto de la ventana en píxeles
            duracion: Duración en milisegundos antes de cerrar (default: 3000 = 3 segundos)
        """
        titulo = titulo or "✓ PASS"
        
        popup = tk.Toplevel()
        popup.title(titulo)
        popup.geometry(f"{ancho}x{alto}")
        popup.resizable(False, False)
        popup.configure(bg="#ccffcc")  # Fondo verde claro
        
        # Centrar la ventana
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (ancho // 2)
        y = (popup.winfo_screenheight() // 2) - (alto // 2)
        popup.geometry(f"{ancho}x{alto}+{x}+{y}")
        popup.transient()
        popup.grab_set()
        frame_contenido = tk.Frame(popup, bg="#000000", padx=20, pady=20)
        frame_contenido.pack(expand=True, fill=tk.BOTH)
        
        # Etiqueta del título con icono
        label_titulo = tk.Label(
            frame_contenido,
            text="PASS",
            font=("Arial", 24, "bold"),
            fg="#33FF00",
            bg="#000000"
        )
        label_titulo.pack(pady=(0, 10))
        
        # Etiqueta del mensaje
        label_mensaje = tk.Label(
            frame_contenido, 
            text=mensaje, 
            wraplength=ancho-40,
            justify=tk.CENTER,
            font=("Arial", 12),
            fg="#FFFFFF",
            bg="#000000"
        )
        label_mensaje.pack(expand=True)
        segundos_restantes = duracion // 1000
        
        def actualizar_cuenta():
            nonlocal segundos_restantes
            if segundos_restantes > 0:
                segundos_restantes -= 1
                popup.after(1000, actualizar_cuenta)
        actualizar_cuenta()
        # Cerrar automáticamente después de la duración especificada
        popup.after(duracion, popup.destroy)
    
        popup.wait_window()
    
# Ejemplo de uso
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Ocultar la ventana principal
    avisos = PopUpAvisos(titulo_app="Sistema MES")
    avisos.timeout("Se ha producido un timeout en la operación.", titulo="Tiempo Agotado")

    