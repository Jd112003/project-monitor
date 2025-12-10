"""
msi_ec_manager.py - Control y lectura de estados expuestos por msi-ec.

Permite leer y escribir fan_mode, shift_mode y cooler_boost usando sysfs.
Es best-effort: si no existe el driver o faltan permisos, devuelve mensajes claros.
"""

from __future__ import annotations

import os
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List


class MsiEcManager:
    """
    Interfaz para los nodos de msi-ec en /sys/devices/platform/msi-ec/.
    """

    BASE = Path("/sys/devices/platform/msi-ec")

    def __init__(self, use_pkexec: bool = False):
        self.use_pkexec = use_pkexec
        self.helper_path = Path(__file__).resolve().parents[2] / "scripts" / "msi_ec_helper.py"

    def is_available(self) -> bool:
        return self.BASE.exists()

    def get_info(self) -> Dict[str, Any]:
        if not self.is_available():
            return {"available": False}
        return {
            "available": True,
            "fan_mode": self._safe_read_str(self.BASE / "fan_mode"),
            "shift_mode": self._safe_read_str(self.BASE / "shift_mode"),
            "available_fan_modes": self._read_list(self.BASE / "available_fan_modes"),
            "available_shift_modes": self._read_list(self.BASE / "available_shift_modes"),
            "cooler_boost": self._safe_read_str(self.BASE / "cooler_boost"),
        }

    def set_fan_mode(self, mode: str) -> Dict[str, Any]:
        return self._write_mode("fan_mode", mode, self.BASE / "available_fan_modes")

    def set_shift_mode(self, mode: str) -> Dict[str, Any]:
        return self._write_mode("shift_mode", mode, self.BASE / "available_shift_modes")

    def set_cooler_boost(self, value: str) -> Dict[str, Any]:
        """
        Ajusta cooler_boost. Acepta "on"/"off" o "1"/"0".
        """
        path = self.BASE / "cooler_boost"
        if not path.exists():
            return {"success": False, "message": "cooler_boost no soportado"}
        norm = value
        if value in ("1", "on", "true", "True"):
            norm = "on"
        elif value in ("0", "off", "false", "False"):
            norm = "off"
        return self._write_value(path, norm)

    # ----- Batería -----
    def get_battery_info(self) -> Dict[str, Any]:
        bat_path = Path("/sys/class/power_supply/BAT1")
        if not bat_path.exists():
            return {}
        return {
            "capacity": self._safe_read_str(bat_path / "capacity"),
            "status": self._safe_read_str(bat_path / "status"),
            "start_threshold": self._safe_read_str(bat_path / "charge_control_start_threshold"),
            "end_threshold": self._safe_read_str(bat_path / "charge_control_end_threshold"),
        }

    def set_battery_thresholds(self, start: Optional[int] = None, end: Optional[int] = None) -> Dict[str, Any]:
        bat_path = Path("/sys/class/power_supply/BAT1")
        if not bat_path.exists():
            return {"success": False, "message": "BAT1 no encontrada"}
        msgs = []
        success = True
        if start is not None:
            res = self._write_value(bat_path / "charge_control_start_threshold", str(int(start)))
            success = success and res.get("success", False)
            msgs.append(res.get("message", ""))
        if end is not None:
            res = self._write_value(bat_path / "charge_control_end_threshold", str(int(end)))
            success = success and res.get("success", False)
            msgs.append(res.get("message", ""))
        return {"success": success, "message": " | ".join([m for m in msgs if m]) or "OK"}

    # ----- Webcam -----
    def set_webcam(self, enable: bool) -> Dict[str, Any]:
        path = self.BASE / "webcam"
        if not path.exists():
            return {"success": False, "message": "webcam no soportada"}
        return self._write_value(path, "on" if enable else "off")

    def set_webcam_block(self, enable: bool) -> Dict[str, Any]:
        path = self.BASE / "webcam_block"
        if not path.exists():
            return {"success": False, "message": "webcam_block no soportada"}
        return self._write_value(path, "on" if enable else "off")

    # ----- Backlight teclado -----
    def set_keyboard_backlight(self, level: int) -> Dict[str, Any]:
        path = Path("/sys/class/leds/msiacpi::kbd_backlight/brightness")
        if not path.exists():
            return {"success": False, "message": "Backlight no soportado"}
        return self._write_value(path, str(int(level)))

    def get_keyboard_backlight(self) -> str:
        path = Path("/sys/class/leds/msiacpi::kbd_backlight/brightness")
        return self._safe_read_str(path)

    # Internos
    def _write_mode(self, filename: str, value: str, available_path: Path) -> Dict[str, Any]:
        path = self.BASE / filename
        if not path.exists():
            return {"success": False, "message": f"{filename} no soportado en este equipo"}
        available = self._read_list(available_path)
        if available and value not in available:
            return {"success": False, "message": f"Valor '{value}' no soportado. Disponibles: {', '.join(available)}"}
        return self._write_value(path, value)

    def _write_value(self, path: Path, value: str) -> Dict[str, Any]:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(value))
            return {"success": True, "message": f"{path.name} ajustado a {value}"}
        except PermissionError:
            if self.use_pkexec:
                return self._run_helper(path.name, str(value))
            return {"success": False, "message": "Permiso denegado (requiere pkexec/root)"}
        except Exception as exc:
            return {"success": False, "message": f"Error escribiendo {path.name}: {exc}"}

    def _run_helper(self, target: str, value: str) -> Dict[str, Any]:
        if not self.helper_path.exists():
            return {"success": False, "message": "Helper msi-ec no encontrado"}
        if not shutil.which("pkexec"):
            return {"success": False, "message": "pkexec no disponible"}
        python_bin = sys.executable or "/usr/bin/python3"
        cmd = ["pkexec", python_bin, str(self.helper_path), f"--{target}", str(value)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {"success": True, "message": result.stdout.strip() or f"{target} aplicado"}
            return {"success": False, "message": result.stderr.strip() or f"pkexec falló ajustando {target}"}
        except subprocess.SubprocessError as exc:
            return {"success": False, "message": f"Error ejecutando pkexec: {exc}"}

    @staticmethod
    def _read_list(path: Path) -> List[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip().split()
        except Exception:
            return []

    @staticmethod
    def _safe_read_str(path: Path) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return ""
