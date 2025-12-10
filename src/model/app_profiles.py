"""
app_profiles.py - Gestión de perfiles por aplicación.

Permite definir en config perfiles que, al aplicarse, cambian gobernador/frecuencia
y (opcionalmente) PWM de ventiladores. Este módulo no detecta ni mata procesos;
solo aplica acciones solicitadas.
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from model.power_manager import PowerManager
from model.fan_manager import FanManager


class AppProfiles:
    """
    Aplica perfiles definidos en configuración.
    """

    def __init__(self, power: PowerManager, fans: FanManager, profiles_cfg: Optional[Dict[str, Any]] = None):
        self.power = power
        self.fans = fans
        self.profiles_cfg = profiles_cfg or {}

    def available_profiles(self):
        return list(self.profiles_cfg.keys())

    def apply_profile(self, name: str) -> Dict[str, Any]:
        cfg = self.profiles_cfg.get(name)
        if not cfg:
            return {"success": False, "message": f"Perfil '{name}' no encontrado"}

        messages = []
        success = True

        governor = cfg.get("governor")
        if governor:
            res = self.power.set_governor(governor)
            messages.append(res.get("message", ""))
            success = success and res.get("success", False)

        max_freq = cfg.get("max_freq_khz")
        if max_freq:
            res = self.power.set_max_freq(int(max_freq))
            messages.append(res.get("message", ""))
            success = success and res.get("success", False)

        pwm = cfg.get("pwm")
        pwm_path = cfg.get("pwm_path")
        if pwm is not None and pwm_path:
            res = self.fans.set_pwm(pwm_path, int(pwm))
            messages.append(res.get("message", ""))
            success = success and res.get("success", False)

        return {"success": success, "message": " | ".join(m for m in messages if m)}
