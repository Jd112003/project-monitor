"""
power_manager.py - Control básico de perfiles de energía en Linux.

Permite leer y escribir gobernadores de CPU y frecuencias máximas por perfil.
Las escrituras requieren permisos; se maneja fallback con pkexec si está habilitado.
"""

from __future__ import annotations

import glob
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Dict, Any, Optional


class PowerManager:
    """
    Gestiona gobernadores de CPU y límites de frecuencia.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.cpu_paths = glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq")
        self.use_pkexec = bool((config or {}).get("use_pkexec", False))
        # helper en la raíz del proyecto (../.. /scripts/power_helper.py)
        self.helper_path = Path(__file__).resolve().parents[2] / "scripts" / "power_helper.py"

    def get_governors(self) -> Dict[str, Any]:
        """
        Obtiene el gobernador actual y los disponibles (primer CPU como referencia).
        """
        if not self.cpu_paths:
            return {"current": None, "available": []}
        path = self.cpu_paths[0]
        current = _safe_read_str(f"{path}/scaling_governor")
        available = _safe_read_str(f"{path}/scaling_available_governors")
        available_list = available.split() if available else []
        max_freq = _safe_read_str(f"{path}/scaling_max_freq")
        min_freq = _safe_read_str(f"{path}/scaling_min_freq")
        return {
            "current": current,
            "available": available_list,
            "max_freq": _safe_int(max_freq),
            "min_freq": _safe_int(min_freq),
        }

    def set_governor(self, governor: str) -> Dict[str, Any]:
        """
        Intenta establecer un gobernador en todos los CPUs.
        """
        if not governor:
            return {"success": False, "message": "Gobernador no especificado"}
        if not self.cpu_paths:
            return {"success": False, "message": "No se encontró ruta cpufreq"}
        # Verificar soporte del gobernador
        available = self.get_governors().get("available") or []
        if available and governor not in available:
            return {
                "success": False,
                "message": f"Gobernador '{governor}' no soportado. Disponibles: {', '.join(available)}",
            }

        errors = []
        for path in self.cpu_paths:
            ok = _safe_write_str(f"{path}/scaling_governor", governor)
            if not ok:
                errors.append(path)
        if errors:
            # Intentar pkexec helper si está habilitado
            if self.use_pkexec:
                res = self._run_helper(governor=governor)
                return res
            return {"success": False, "message": f"No se pudo escribir en {len(errors)} CPU(s). Requiere permisos."}
        return {"success": True, "message": f"Gobernador establecido en '{governor}'"}

    def set_max_freq(self, khz: int) -> Dict[str, Any]:
        """
        Establece la frecuencia máxima en kHz para todos los CPUs (requiere permisos).
        """
        if not khz or khz <= 0:
            return {"success": False, "message": "Frecuencia inválida"}
        if not self.cpu_paths:
            return {"success": False, "message": "No se encontró ruta cpufreq"}
        errors = []
        for path in self.cpu_paths:
            ok = _safe_write_str(f"{path}/scaling_max_freq", str(int(khz)))
            if not ok:
                errors.append(path)
        if errors:
            if self.use_pkexec:
                res = self._run_helper(max_freq_khz=int(khz))
                return res
            return {"success": False, "message": f"No se pudo escribir en {len(errors)} CPU(s). Requiere permisos."}
        return {"success": True, "message": f"Frecuencia máxima ajustada a {khz} kHz"}

    def _run_helper(self, governor: Optional[str] = None, max_freq_khz: Optional[int] = None) -> Dict[str, Any]:
        """
        Ejecuta el helper con pkexec para aplicar cambios con privilegios.
        """
        if not self.helper_path.exists():
            return {"success": False, "message": "Helper de energía no encontrado"}
        if not shutil.which("pkexec"):
            return {"success": False, "message": "pkexec no disponible para elevar privilegios"}

        python_bin = sys.executable or "/usr/bin/python3"
        cmd = ["pkexec", python_bin, str(self.helper_path)]
        if governor:
            cmd += ["--governor", str(governor)]
        if max_freq_khz:
            cmd += ["--max-freq-khz", str(int(max_freq_khz))]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {"success": True, "message": result.stdout.strip() or "Perfil aplicado con pkexec"}
            else:
                return {"success": False, "message": result.stderr.strip() or "pkexec falló en aplicar el perfil"}
        except subprocess.SubprocessError as exc:
            return {"success": False, "message": f"Error ejecutando pkexec: {exc}"}


def _safe_read_str(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.readline().strip()
    except Exception:
        return ""


def _safe_write_str(path: str, value: str) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(value)
        return True
    except Exception:
        return False


def _safe_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None
