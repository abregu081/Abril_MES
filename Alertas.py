# popup.py
import tkinter as tk
from tkinter import messagebox

class Popup:
    """
    Clase utilitaria para generar pop‑ups de aviso usando Tkinter.
    - success(): muestra un mensaje de éxito (icono 'info')
    - error():   muestra un mensaje de error (icono 'error')
    - info():    muestra un mensaje genérico (icono 'warning' o 'info')
    """

    def __init__(self, title="Aplicación"):
        """
        Crea una ventana raíz oculta que sirve como padre de los diálogos.
        Parámetros
        ----------
        title : str
            Título que aparecerá en la barra de la ventana raíz (no visible para el usuario).
        """
        # La ventana raíz solo se necesita para que los messagebox tengan un "parent".
        self.root = tk.Tk()
        self.root.withdraw()          # Oculta la ventana principal
        self.root.title(title)

    def success(self, mensaje: str, titulo: str = "Éxito"):
        """
        Muestra un cuadro de diálogo de tipo *info* indicando que la operación fue exitosa.
        """
        messagebox.showinfo(titulo, mensaje, parent=self.root)

    def error(self, mensaje: str, titulo: str = "Error"):
        """
        Muestra un cuadro de diálogo de tipo *error* indicando que la operación falló.
        """
        messagebox.showerror(titulo, mensaje, parent=self.root)

    def info(self, mensaje: str, titulo: str = "Información", icon: str = "info"):
        """
        Muestra un cuadro de diálogo genérico.
        Parámetros
        ----------
        mensaje : str
            Texto a presentar al usuario.
        titulo  : str
            Título de la ventana del pop‑up.
        icon    : str  {'info', 'warning', 'question'}
            Tipo de icono que se quiere usar.
        """
        # Seleccionamos la función adecuada según el icono solicitado
        if icon == "info":
            messagebox.showinfo(titulo, mensaje, parent=self.root)
        elif icon == "warning":
            messagebox.showwarning(titulo, mensaje, parent=self.root)
        elif icon == "question":
            messagebox.askquestion(titulo, mensaje, parent=self.root)
        else:
            # Por seguridad, si se pasa un icono no reconocido usamos info.
            messagebox.showinfo(titulo, mensaje, parent=self.root)

    def ask_yes_no(self, mensaje: str, titulo: str = "Confirmación"):
        """
        Pregunta sí/no al usuario y devuelve True (Sí) o False (No).
        """
        respuesta = messagebox.askyesno(titulo, mensaje, parent=self.root)
        return respuesta

    def close(self):
        """
        Libera los recursos de la ventana raíz.
        Normalmente no es necesario llamarlo porque al terminar el script
        Python cierra automáticamente la ventana, pero es útil si reutilizas la clase.
        """
        self.root.destroy()


# ----------------------------------------------------------------------
# Ejemplo de uso (puedes copiar‑pegar esto en otro archivo para probar)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    pop = Popup("Demo de Pop‑ups")
    
    # Mensaje de éxito
    pop.success("Los datos se guardaron correctamente.", "Operación completada")
    
    # Mensaje de error
    pop.error("No se pudo conectar al servidor.", "Fallo de conexión")
    
    # Cerrar la ventana raíz cuando ya no es necesaria
    pop.close()
