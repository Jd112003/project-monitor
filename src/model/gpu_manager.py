"""
gpu_manager.py - Detección básica de GPU (NVIDIA/AMD) y métricas.

Usa nvidia-smi o rocm-smi si están disponibles para obtener uso, temperatura y VRAM.
Best-effort: si no hay comandos o permisos, devuelve None.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Dict, Any, List, Optional


class GPUManager:
    """
    Lee métricas de GPU si el sistema lo permite.
    """

    def get_gpu_info(self) -> List[Dict[str, Any]]:
        """
        Devuelve lista de GPUs detectadas con métricas comunes.
        """
        # Prioridad: NVIDIA -> AMD (ROC)
        nvidia = self._get_nvidia_smi()
        if nvidia:
            return nvidia
        amd = self._get_rocm_smi()
        if amd:
            return amd
        return []

    def _get_nvidia_smi(self) -> List[Dict[str, Any]]:
        if not shutil.which("nvidia-smi"):
            return []
        query = [
            "--query-gpu=name,index,utilization.gpu,utilization.memory,memory.total,memory.used,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
        ]
        try:
            result = subprocess.run(
                ["nvidia-smi"] + query,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if result.returncode != 0:
                return []
            gpus = []
            for line in result.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 8:
                    continue
                gpus.append(
                    {
                        "vendor": "NVIDIA",
                        "name": parts[0],
                        "index": int(parts[1]),
                        "utilization": float(parts[2]),
                        "mem_util": float(parts[3]),
                        "mem_total_mb": float(parts[4]),
                        "mem_used_mb": float(parts[5]),
                        "temperature": float(parts[6]),
                        "power_w": float(parts[7]),
                    }
                )
            return gpus
        except Exception:
            return []

    def _get_rocm_smi(self) -> List[Dict[str, Any]]:
        if not shutil.which("rocm-smi") and not shutil.which("amd-smi"):
            return []
        cmd = shutil.which("rocm-smi") or shutil.which("amd-smi")
        try:
            result = subprocess.run(
                [cmd, "--showtemp", "--showuse", "--showmeminfo", "vram", "--json"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            data = json.loads(result.stdout or "{}")
            gpus = []
            for key, info in data.get("card", {}).items():
                gpus.append(
                    {
                        "vendor": "AMD",
                        "name": info.get("Card series") or key,
                        "index": int(key.replace("card", "")) if key.startswith("card") else len(gpus),
                        "utilization": _safe_float(info.get("GPU use (%)")),
                        "mem_util": _safe_float(info.get("GPU memory use (%)")),
                        "mem_total_mb": _safe_float(info.get("VRAM Total Memory (B)")) / (1024 * 1024),
                        "mem_used_mb": _safe_float(info.get("VRAM Used Memory (B)")) / (1024 * 1024),
                        "temperature": _safe_float(info.get("Temperature (Sensor edge) (C)")),
                        "power_w": _safe_float(info.get("Average Graphics Package Power (W)")),
                    }
                )
            return gpus
        except Exception:
            return []


def _safe_float(val: Optional[Any]) -> float:
    try:
        return float(val)
    except Exception:
        return 0.0
