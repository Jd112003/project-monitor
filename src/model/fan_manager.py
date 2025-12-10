"""
fan_manager.py - Control básico de ventiladores vía sysfs (hwmon).

Permite listar ventiladores y ajustar PWM si está disponible y se poseen permisos.
Se basa en hwmon ya detectado por SensorsReader; este módulo añade escritura segura.
"""

from __future__ import annotations

from typing import Dict, Any

from model.sensors import SensorsReader


class FanManager:
    """
    Gestiona lectura y ajuste de ventiladores usando SensorsReader.
    """

    def __init__(self):
        self._sensors = SensorsReader()

    def list_fans(self):
        return self._sensors.get_fans()

    def set_pwm(self, pwm_path: str, value: int) -> Dict[str, Any]:
        return self._sensors.set_pwm(pwm_path, value)
