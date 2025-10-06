SET _version=1.0.0.0
SET _PATH_SOURCE=%CD%\
SET _WIN_=exe.win-amd64-3.11\

@echo.
@echo **************
@echo * COMPILANDO *
@echo **************
@echo.

python "%_PATH_SOURCE%setup.py" build 


@echo.
@echo *********************
@echo * COPIANDO ARCHIVOS *
@echo *********************
@echo.

Copy "%_PATH_SOURCE%Setting.ini" "%_PATH_SOURCE%build\%_WIN_%"
Copy "%_PATH_SOURCE%MES_settings.ini" "%_PATH_SOURCE%build\%_WIN_%"

@echo.
@echo * Proceso Terminado *
@echo.
timeout /t 3
