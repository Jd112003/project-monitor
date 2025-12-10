"""
config.py - Carga de configuración de la aplicación.

Permite ajustar intervalos de actualización, umbrales de alerta y opciones de UI.
Si existe un archivo config.json en la raíz del proyecto, se carga y
sobrescribe los valores por defecto.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "update_interval": 2.0,
    "history_duration": 3600,
    "process_refresh_interval": 5.0,
    "process_list_limit": 50,
    "use_pkexec": False,
    "alerts": {
        "cpu_warn": 85.0,
        "cpu_crit": 95.0,
        "ram_warn": 85.0,
        "ram_crit": 95.0,
    },
    "theme": "dark",
    "rgb_enabled": False,
    "power_profiles": {
        "Silencioso": {"governor": "powersave"},
        "Equilibrado": {"governor": "schedutil"},
        "Rendimiento": {"governor": "performance"},
    },
    "profiles": {
        "juego": {"governor": "performance", "max_freq_khz": None},
        "bajo_consumo": {"governor": "powersave"},
    },
}


def load_config() -> Dict[str, Any]:
    """
    Carga config.json si existe en la raíz del proyecto, fusionando con defaults.
    """
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "config.json"
    config = DEFAULT_CONFIG.copy()

    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                _deep_update(config, user_cfg)
        except Exception:
            # Si falla, usamos los defaults y seguimos.
            pass

    return config


def _deep_update(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """Actualiza recursivamente un diccionario destino con valores de otro."""
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
