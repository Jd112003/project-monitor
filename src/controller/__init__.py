"""
controller - Módulo de Control de la Aplicación

Este paquete contiene las clases del Controlador en el patrón MVC:
- AppController: Controlador principal de la aplicación
- ThreadManager: Gestión de hilos para tareas asíncronas
"""

from .app_controller import AppController
from .thread_manager import ThreadManager

__all__ = ['AppController', 'ThreadManager']
