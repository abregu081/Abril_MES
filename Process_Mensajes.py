import os
import sys
import Controller_Error
import Setting as ST

class procesador:
    def __init__(self,Mensaje, n_char):
        self.mensaje = Mensaje
        self.n_char = n_char
    
    @staticmethod
    def validor_mensaje(self):
        mensaje = self.mensaje
        if len(mensaje) > self.n_char:
            print(f"[Debug] - Tipo de caracterer invalido y no apto verificar la entrada del mismo")
        else:
            pass

