#!/usr/bin/env python3
"""
power_helper.py - Helper privilegiado para ajustar gobernador/frecuencia.

Se espera ser invocado con pkexec:
  pkexec python3 scripts/power_helper.py --governor performance
"""

from __future__ import annotations

import argparse
import glob
import sys


def write_governor(governor: str) -> bool:
    cpu_paths = glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq")
    if not cpu_paths:
        print("No se encontraron rutas cpufreq", file=sys.stderr)
        return False
    success = 0
    for path in cpu_paths:
        gov_path = f"{path}/scaling_governor"
        try:
            with open(gov_path, "w", encoding="utf-8") as f:
                f.write(governor)
            success += 1
        except Exception as exc:
            print(f"Fallo escribiendo {gov_path}: {exc}", file=sys.stderr)
            continue
    return success > 0


def write_max_freq(khz: int) -> bool:
    cpu_paths = glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq")
    if not cpu_paths:
        print("No se encontraron rutas cpufreq", file=sys.stderr)
        return False
    success = 0
    for path in cpu_paths:
        freq_path = f"{path}/scaling_max_freq"
        try:
            with open(freq_path, "w", encoding="utf-8") as f:
                f.write(str(int(khz)))
            success += 1
        except Exception as exc:
            print(f"Fallo escribiendo {freq_path}: {exc}", file=sys.stderr)
            continue
    return success > 0


def main():
    parser = argparse.ArgumentParser(description="Helper para ajustar gobernador/frecuencia (requiere root).")
    parser.add_argument("--governor", type=str, help="Gobernador a aplicar (performance, powersave, etc.)")
    parser.add_argument("--max-freq-khz", type=int, help="Frecuencia máxima en kHz")
    args = parser.parse_args()

    if not args.governor and not args.max_freq_khz:
        print("Nada que aplicar", file=sys.stderr)
        return 1

    if args.governor:
        if write_governor(args.governor):
            print(f"Gobernador establecido a {args.governor}")
        else:
            print("No se pudo escribir gobernador (revisar permisos o cpufreq)", file=sys.stderr)
            return 1

    if args.max_freq_khz:
        if write_max_freq(args.max_freq_khz):
            print(f"Frecuencia máxima fijada a {args.max_freq_khz} kHz")
        else:
            print("No se pudo escribir frecuencia máxima (revisar permisos o cpufreq)", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
