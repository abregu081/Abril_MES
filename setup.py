#!/usr/bin/python
# -*- coding: utf-8 -*-

from cx_Freeze import setup, Executable

includes = []
includefiles = []
excludes = ['Tkinter']
packages = ['SerialCOM',"Setting","Consultas_SIM","threading","serial","queue",'Controller_Error', 'Conexiones_MES', 'datetime',"socket","os","sys","time","LogCreator"]

setup(
 name="TestSnifferMirgor",
 version="1.0",
 description="Normaliza datos de logs modificados por los traductores y los almacena en base de datos",
 options = {'build_exe': {'excludes':excludes,'packages':packages,'include_files':includefiles}}, 
 executables = [Executable("Main.py")],
 )

build_exe_options = {
                 "includes":      includes,
}