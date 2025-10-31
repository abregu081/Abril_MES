#!/usr/bin/python
# -*- coding: utf-8 -*-

from cx_Freeze import setup, Executable
import sys
import os

# Detectar ubicación de pywin32_system32
pywin32_path = None
for path in sys.path:
    potential_path = os.path.join(path, 'pywin32_system32')
    if os.path.exists(potential_path):
        pywin32_path = potential_path
        break

includes = []
includefiles = [
    'setting.ini',
    'MES_settings.ini',
    'comandos.ini',
    'Setting_Escaner.ini'
]

# Incluir DLLs de pywin32 si se encuentran
if pywin32_path:
    for file in os.listdir(pywin32_path):
        if file.endswith('.dll'):
            includefiles.append((os.path.join(pywin32_path, file), file))
    print(f"✓ DLLs de pywin32 encontradas en: {pywin32_path}")
else:
    print("⚠ Advertencia: No se encontró pywin32_system32. Ejecute: pip install pywin32")

excludes = []
packages = [
    'SerialCOM',
    'Setting',
    'Consultas_SIM',
    'threading',
    'serial',
    'queue',
    'Controller_Error',
    'Conexiones_MES',
    'datetime',
    'socket',
    'os',
    'sys',
    'time',
    'LogCreator',
    'Alertas',
    'CierreAutomatico',
    'typing',
    'pyautogui',
    'win32gui',
    'win32con',
    'win32api',
    'win32com',
    'pywintypes',
    'pywin32_system32',
    'tkinter',
    'numpy',
    'numpy.core',
    'numpy.core._multiarray_umath',
    'cv2',
    'PIL',
]

# Opciones de build
build_exe_options = {
    'packages': packages,
    'excludes': excludes,
    'include_files': includefiles,
    'includes': includes,
    'include_msvcr': True,  # Incluir runtime de Visual C++
    'optimize': 1,
}

setup(
    name="AtornilladorasMirgor",
    version="1.0",
    description="Sistema MES Abril - Control de Atornilladoras",
    options={'build_exe': build_exe_options},
    executables=[Executable("Main.py", base=None)],  # base=None para mostrar consola
)