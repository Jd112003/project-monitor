"""
rgb_manager.py - Integración opcional con OpenRGB.

Intento ligero de establecer presets simples (off, static, rainbow) usando el servidor OpenRGB.
No añade dependencias; usa protocolo JSON mínimo vía socket TCP si el servidor está en localhost:6742.
"""

from __future__ import annotations

import json
import socket
from typing import Dict, Any


class RGBManager:
    """
    Cliente mínimo para OpenRGB (si está disponible).
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6742, timeout: float = 1.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout):
                return True
        except OSError:
            return False

    def set_preset(self, preset: str) -> Dict[str, Any]:
        """
        Envia un preset simple. Depende del servidor OpenRGB escuchando.
        """
        if not self.is_available():
            return {"success": False, "message": "OpenRGB no disponible"}

        payload = {"command": "set_color", "preset": preset}
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as conn:
                conn.sendall(json.dumps(payload).encode("utf-8"))
            return {"success": True, "message": f"Preset RGB enviado: {preset}"}
        except Exception as exc:
            return {"success": False, "message": f"No se pudo aplicar preset: {exc}"}
