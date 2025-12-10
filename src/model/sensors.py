"""
sensors.py - Lectura de sensores térmicos y ventiladores.

Proporciona una capa de acceso a temperaturas de CPU/GPU (si psutil las expone)
y velocidades de ventilador vía /sys/class/hwmon cuando está disponible.
Todo es best-effort: si no se puede leer, devuelve None.
"""

from __future__ import annotations

import os
from typing import Dict, Any, List, Optional

import psutil


class SensorsReader:
    """
    Lee temperaturas y ventiladores desde psutil y /sys.
    """

    def get_temperatures(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Devuelve temperaturas agrupadas por etiqueta.
        """
        temps = {}
        try:
            raw = psutil.sensors_temperatures(fahrenheit=False)
        except Exception:
            return temps

        for name, entries in raw.items():
            temps[name] = []
            for entry in entries:
                temps[name].append(
                    {
                        "label": entry.label or name,
                        "current": entry.current,
                        "high": getattr(entry, "high", None),
                        "critical": getattr(entry, "critical", None),
                    }
                )
        # Añadir temperaturas de msi-ec si están disponibles
        msi_temps = self._read_msi_ec_temperatures()
        if msi_temps:
            temps["msi-ec"] = msi_temps

        return temps

    def get_fans(self) -> List[Dict[str, Any]]:
        """
        Devuelve lista de ventiladores detectados con velocidad RPM y pwm si existe.
        """
        fans = []
        try:
            sensor_fans = psutil.sensors_fans()
        except Exception:
            sensor_fans = {}

        for name, entries in sensor_fans.items():
            for entry in entries:
                fans.append(
                    {
                        "label": entry.label or name,
                        "rpm": entry.current,
                        "path": None,
                        "pwm": None,
                    }
                )

        # Intentar leer /sys/class/hwmon para obtener pwm ajustable
        hwmon_base = "/sys/class/hwmon"
        if os.path.isdir(hwmon_base):
            for hwmon in os.listdir(hwmon_base):
                hw_path = os.path.join(hwmon_base, hwmon)
                name_path = os.path.join(hw_path, "name")
                try:
                    with open(name_path, "r", encoding="utf-8") as f:
                        hw_name = f.readline().strip()
                except Exception:
                    hw_name = hwmon

                # Mapear fanX_input y pwmX
                for entry in os.listdir(hw_path):
                    if entry.startswith("fan") and entry.endswith("_input"):
                        prefix = entry.split("_")[0]  # fan1
                        rpm_path = os.path.join(hw_path, entry)
                        pwm_path = os.path.join(hw_path, f"{prefix.replace('fan', 'pwm')}")
                        rpm_val = _safe_read_int(rpm_path)
                        pwm_val = _safe_read_int(pwm_path) if os.path.exists(pwm_path) else None
                        fans.append(
                            {
                                "label": f"{hw_name}-{prefix}",
                                "rpm": rpm_val,
                                "path": rpm_path,
                                "pwm": pwm_val,
                                "pwm_path": pwm_path if os.path.exists(pwm_path) else None,
                            }
                        )
        # Añadir lectura de msi-ec si existe
        msi_fans = self._read_msi_ec_fans()
        fans.extend(msi_fans)
        return fans

    def set_pwm(self, pwm_path: str, value: int) -> Dict[str, Any]:
        """
        Intenta escribir un valor PWM (0-255). Requiere permisos de escritura.
        """
        try:
            if value < 0 or value > 255:
                return {"success": False, "message": "PWM fuera de rango (0-255)"}
            with open(pwm_path, "w", encoding="utf-8") as f:
                f.write(str(int(value)))
            return {"success": True, "message": f"PWM ajustado a {value}"}
        except PermissionError:
            return {"success": False, "message": "Permiso denegado al escribir PWM"}
        except Exception as exc:
            return {"success": False, "message": f"Error al escribir PWM: {exc}"}

    def _read_msi_ec_temperatures(self) -> List[Dict[str, Any]]:
        """
        Lee temperaturas desde /sys/devices/platform/msi-ec/{cpu,gpu}/realtime_temperature.
        """
        base = "/sys/devices/platform/msi-ec"
        results: List[Dict[str, Any]] = []
        for label in ("cpu", "gpu"):
            path = os.path.join(base, label, "realtime_temperature")
            value = _safe_read_int(path)
            if value is not None:
                results.append({"label": f"msi-ec {label}", "current": float(value), "high": None, "critical": None})
        return results

    def _read_msi_ec_fans(self) -> List[Dict[str, Any]]:
        """
        Lee velocidad de ventiladores desde /sys/devices/platform/msi-ec/{cpu,gpu}/realtime_fan_speed.
        """
        base = "/sys/devices/platform/msi-ec"
        fans: List[Dict[str, Any]] = []
        for label in ("cpu", "gpu"):
            path = os.path.join(base, label, "realtime_fan_speed")
            value = _safe_read_int(path)
            if value is not None:
                fans.append(
                    {
                        "label": f"msi-ec-{label}",
                        "rpm": value,
                        "path": path,
                        "pwm": None,
                        "pwm_path": None,
                        "source": "msi-ec",
                    }
                )
        return fans


def _safe_read_int(path: str) -> Optional[int]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(f.readline().strip())
    except Exception:
        return None
