import os
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

__all__ = ["LogManager"]

class LogManager:
    """
    Gestor de logs para comunicaciones SIM con auto-rotación mensual.
    
    Estructura de directorios:
        logs/
        ├── PASS/
        │   ├── 2025-10-20/
        │   │   ├── SN12345_PASS_20251020_143000.txt
        │   │   └── ...
        ├── FAIL/
        │   ├── 2025-10-20/
        │   │   ├── SN67890_FAIL_20251020_144500.txt
        │   │   └── ...
    
    Contenido del log:
        - BREQ: Mensaje enviado y respuesta recibida
        - BCMP: Mensaje enviado y respuesta recibida
        - Timestamps en cada línea
    
    Usage:
        logger = LogManager(base_dir)
        
        # Método 1: Guardar con mensajes BREQ y BCMP
        logger.save_sim_communication(
            sn="SN12345",
            breq_sent="BREQ|process=...|id=SN12345|...",
            breq_resp="BCNF|status=PASS|...",
            bcmp_sent="BCMP|process=...|status=PASS|...",
            bcmp_resp="BACK|status=PASS|...",
            is_pass=True
        )
        
        # Método 2: Guardar lista de mensajes (compatible con código anterior)
        logger.save(sn, messages, is_pass=True)
    """

    def __init__(self, base_dir: str, auto_rotate: bool = True):
        """
        Inicializa el gestor de logs.
        
        Args:
            base_dir: Directorio base para los logs
            auto_rotate: Si True, organiza logs en subcarpetas por año-mes (default: True)
        """
        self.base_dir = os.path.abspath(base_dir)
        self.auto_rotate = auto_rotate
        
        # Crear carpetas base
        for sub in ("PASS", "FAIL"):
            os.makedirs(os.path.join(self.base_dir, sub), exist_ok=True)

    # ------------------------------------------------------------------
    # Método Principal para Comunicaciones SIM
    # ------------------------------------------------------------------
    def save_sim_communication(
        self,
        sn: str,
        breq_sent: str,
        breq_resp: str,
        bcmp_sent: Optional[str] = None,
        bcmp_resp: Optional[str] = None,
        is_pass: bool = True,
        additional_info: Optional[dict] = None
    ) -> str:
        """
        Guarda las comunicaciones BREQ y BCMP con el sistema SIM.
        
        Args:
            sn: Serial Number
            breq_sent: Mensaje BREQ enviado a SIM
            breq_resp: Respuesta BCNF recibida de SIM
            bcmp_sent: Mensaje BCMP enviado a SIM (opcional)
            bcmp_resp: Respuesta BACK recibida de SIM (opcional)
            is_pass: True si el resultado es PASS, False si es FAIL
            additional_info: Información adicional para incluir en el log (opcional)
        
        Returns:
            Path completo del archivo creado
        """
        resultado = "PASS" if is_pass else "FAIL"
        
        # Construir el contenido del log
        lines = []
        lines.append("=" * 80)
        lines.append("LOG DE COMUNICACIÓN SIM - SISTEMA ABRIL-SIM")
        lines.append("=" * 80)
        lines.append(f"Serial Number:  {sn}")
        lines.append(f"Resultado:      {resultado}")
        lines.append(f"Fecha/Hora:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        lines.append("")
        
        # Información adicional si existe
        if additional_info:
            lines.append("--- INFORMACIÓN ADICIONAL ---")
            for key, value in additional_info.items():
                lines.append(f"{key}: {value}")
            lines.append("")
        
        # Sección BREQ
        lines.append("--- BREQ (BEGIN REQUEST) ---")
        lines.append(f"[{self._get_timestamp()}] ENVIADO → {breq_sent}")
        lines.append(f"[{self._get_timestamp()}] RECIBIDO ← {breq_resp}")
        lines.append("")
        
        # Sección BCMP (si existe)
        if bcmp_sent and bcmp_resp:
            lines.append("--- BCMP (BEGIN COMPLETE) ---")
            lines.append(f"[{self._get_timestamp()}] ENVIADO → {bcmp_sent}")
            lines.append(f"[{self._get_timestamp()}] RECIBIDO ← {bcmp_resp}")
            lines.append("")
        
        # Footer
        lines.append("=" * 80)
        lines.append(f"Fin del log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        
        # Guardar usando el método save
        return self.save(sn, lines, is_pass, resultado=resultado)

    # ------------------------------------------------------------------
    # Método de Guardado General
    # ------------------------------------------------------------------
    def save(
        self, 
        sn: str, 
        messages: Iterable[str], 
        is_pass: bool,
        resultado: Optional[str] = None
    ) -> str:
        """
        Guarda mensajes en formato texto con auto-rotación por mes.

        Args:
            sn: Serial number para el nombre del archivo
            messages: Iterable con las líneas a guardar
            is_pass: True → PASS, False → FAIL
            resultado: String del resultado (PASS/FAIL) para el nombre del archivo

        Returns:
            Path completo del archivo creado
        """
        folder = "PASS" if is_pass else "FAIL"
        
        # Auto-rotación: crear subcarpeta por año-mes-día
        if self.auto_rotate:
            date_folder = datetime.now().strftime("%Y-%m-%d")
            folder = os.path.join(folder, date_folder)
            full_folder_path = os.path.join(self.base_dir, folder)
            os.makedirs(full_folder_path, exist_ok=True)
        
        # Generar nombre del archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sn_clean = self._sanitize_sn(sn)
        
        # Incluir resultado en el nombre si se proporciona
        if resultado:
            filename = f"{sn_clean}_{resultado}_{timestamp}.txt"
        else:
            filename = f"{sn_clean}_{timestamp}.txt"
        
        full_path = os.path.join(self.base_dir, folder, filename)

        # Escribir el archivo
        with open(full_path, "w", encoding="utf-8") as fh:
            for line in messages:
                fh.write(str(line).rstrip() + "\n")

        return full_path

    # ------------------------------------------------------------------
    # Método Simple para Guardar Solo BREQ/BCMP
    # ------------------------------------------------------------------
    def save_breq_bcmp(
        self,
        sn: str,
        breq_tuple: Tuple[bool, str, str],
        bcmp_tuple: Optional[Tuple[bool, str, str]] = None,
        is_pass: bool = True
    ) -> str:
        """
        Guarda comunicaciones usando las tuplas que retornan los métodos de Consultas_SIM.
        
        Args:
            sn: Serial Number
            breq_tuple: Tupla (ok, mensaje_enviado, respuesta) del BREQ
            bcmp_tuple: Tupla (ok, mensaje_enviado, respuesta) del BCMP (opcional)
            is_pass: True para PASS, False para FAIL
        
        Returns:
            Path del archivo creado
        
        Example:
            # Desde Consultas_SIM obtienes:
            ok_breq, breq_msg, breq_resp = consultas._check_sn()
            ok_bcmp, bcmp_msg, bcmp_resp = consultas._check_bcmp(resultado)
            
            # Guardar:
            logger.save_breq_bcmp(
                sn=sn_actual,
                breq_tuple=(ok_breq, breq_msg, breq_resp),
                bcmp_tuple=(ok_bcmp, bcmp_msg, bcmp_resp),
                is_pass=ok_bcmp
            )
        """
        # Extraer datos de BREQ
        breq_ok, breq_sent, breq_resp = breq_tuple
        
        # Extraer datos de BCMP si existe
        bcmp_sent = None
        bcmp_resp = None
        if bcmp_tuple:
            bcmp_ok, bcmp_sent, bcmp_resp = bcmp_tuple
        
        # Usar el método principal
        return self.save_sim_communication(
            sn=sn,
            breq_sent=breq_sent,
            breq_resp=breq_resp,
            bcmp_sent=bcmp_sent,
            bcmp_resp=bcmp_resp,
            is_pass=is_pass
        )

    # ------------------------------------------------------------------
    # Métodos de Utilidad
    # ------------------------------------------------------------------
    @staticmethod
    def _get_timestamp() -> str:
        """Retorna timestamp en formato legible."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    @staticmethod
    def _sanitize_sn(sn: str) -> str:
        """Elimina caracteres no seguros para nombres de archivo."""
        return "".join(c for c in sn if c.isalnum() or c in ("-", "_"))
