#!/usr/bin/env python3
"""
msi_ec_helper.py - Helper privilegiado para escribir fan_mode, shift_mode, cooler_boost y brillo teclado.

Se ejecuta con pkexec:
  pkexec python3 scripts/msi_ec_helper.py --fan_mode auto
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

BASE = Path("/sys/devices/platform/msi-ec")
BRIGHTNESS_PATH = Path("/sys/class/leds/msiacpi::kbd_backlight/brightness")


def write_value(path: Path, value: str) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(value))
        return True
    except Exception as exc:
        print(f"Error escribiendo {path}: {exc}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Helper msi-ec (requiere root).")
    parser.add_argument("--fan_mode", type=str, help="Modo de ventilador (auto/silent/basic/advanced)")
    parser.add_argument("--shift_mode", type=str, help="Modo shift (eco/comfort/sport/turbo, según soporte)")
    parser.add_argument("--cooler_boost", type=str, help="0/1 o on/off para cooler_boost")
    parser.add_argument("--brightness", type=int, help="0-3 brillo teclado (msi backlight)")
    args = parser.parse_args()

    if not (args.fan_mode or args.shift_mode or args.cooler_boost or args.brightness is not None):
        print("Nada que aplicar", file=sys.stderr)
        return 1

    ok = True
    if args.fan_mode:
        ok = write_value(BASE / "fan_mode", args.fan_mode) and ok
    if args.shift_mode:
        ok = write_value(BASE / "shift_mode", args.shift_mode) and ok
    if args.cooler_boost is not None:
        ok = write_value(BASE / "cooler_boost", args.cooler_boost) and ok
    if args.brightness is not None:
        ok = write_value(BRIGHTNESS_PATH, str(int(args.brightness))) and ok

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
