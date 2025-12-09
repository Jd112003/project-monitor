"""
model - Módulo de Datos del Sistema

Este paquete contiene las clases del Modelo en el patrón MVC:
- SystemData: Recopilación de métricas del sistema
- ProcessManager: Gestión de procesos
"""

from .system_data import SystemData
from .process_manager import ProcessManager

__all__ = ['SystemData', 'ProcessManager']
