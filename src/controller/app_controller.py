"""
app_controller.py - Controlador Principal de la Aplicación

Este módulo contiene la clase AppController que implementa la lógica
central del patrón MVC, coordinando el Modelo y la Vista.

Autor: Project Monitor Team
"""

import time
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from collections import deque

# Importar módulos del modelo
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model.system_data import SystemData
from model.process_manager import ProcessManager
from controller.thread_manager import ThreadManager


class AppController:
    """
    Controlador principal de la aplicación de monitoreo.
    
    Implementa el patrón MVC coordinando:
    - Model: SystemData y ProcessManager para obtener datos
    - View: (Simulada) Imprime datos por consola; será reemplazada por GUI
    - Controller: Esta clase, que orquesta la lógica de la aplicación
    """
    
    # Constantes
    UPDATE_INTERVAL = 2.0  # Intervalo de actualización en segundos
    HISTORY_DURATION = 3600  # Duración del historial en segundos (1 hora)
    MAX_HISTORY_ENTRIES = HISTORY_DURATION // int(UPDATE_INTERVAL)  # ~1800 entradas
    
    def __init__(self):
        """
        Inicializa el controlador de la aplicación.
        
        Instancia los componentes del modelo y el gestor de hilos.
        """
        # Instanciar componentes del Modelo
        self._system_data = SystemData()
        self._process_manager = ProcessManager()
        
        # Instanciar el gestor de hilos
        self._thread_manager = ThreadManager()
        
        # Estructura para almacenar el historial de métricas (últimas 1 hora)
        # Usamos deque con maxlen para que automáticamente descarte los más antiguos
        self._metrics_history: deque = deque(maxlen=int(self.MAX_HISTORY_ENTRIES))
        
        # Datos actuales (última lectura)
        self._current_metrics: Optional[Dict[str, Any]] = None
        
        # Flag para controlar si el monitoreo está activo
        self._is_monitoring = False
        
        # Callback opcional para notificar a la Vista de actualizaciones
        # En una implementación real con GUI, aquí se conectaría el callback
        # que actualiza los widgets de la interfaz
        self._view_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        
        print("[AppController] Controller initialized.")
    
    def set_view_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Establece el callback que será llamado cuando hay nuevos datos.
        
        En una implementación con GUI, este callback actualizaría los widgets.
        
        Args:
            callback: Función que recibe los datos actualizados.
        """
        self._view_callback = callback
        print("[AppController] View callback registered.")
    
    def update_metrics(self) -> None:
        """
        Actualiza las métricas del sistema.
        
        Este método:
        1. Llama a los métodos del Modelo para obtener datos actuales
        2. Almacena los datos en el historial
        3. Notifica a la Vista (imprime por consola o llama al callback)
        
        Es llamado periódicamente por el ThreadManager.
        """
        try:
            # Obtener todas las métricas del sistema
            self._current_metrics = self._system_data.get_all_metrics()
            
            # Agregar timestamp de lectura
            self._current_metrics['read_time'] = datetime.now().isoformat()
            
            # Almacenar en el historial (deque maneja automáticamente el límite)
            self._metrics_history.append({
                'timestamp': self._current_metrics['timestamp'],
                'cpu_percent': self._current_metrics['cpu']['total_percent'],
                'ram_percent': self._current_metrics['ram']['percent'],
                'network_upload': self._current_metrics['network']['upload_speed'],
                'network_download': self._current_metrics['network']['download_speed']
            })
            
            # Notificar a la Vista
            self._notify_view()
            
        except Exception as e:
            print(f"[AppController] Error updating metrics: {e}")
    
    def _notify_view(self) -> None:
        """
        Notifica a la Vista que hay nuevos datos disponibles.
        
        Por defecto, imprime los datos por consola.
        Si hay un callback registrado, lo llama con los datos.
        """
        if self._current_metrics is None:
            return
        
        # Si hay un callback de Vista registrado, usarlo
        if self._view_callback:
            self._view_callback(self._current_metrics)
            return
        
        # Comportamiento por defecto: imprimir por consola
        self._print_metrics_to_console()
    
    def _print_metrics_to_console(self) -> None:
        """
        Imprime las métricas actuales por consola (Vista simulada).
        
        Este método actúa como un placeholder para la Vista real.
        En producción, sería reemplazado por la actualización de widgets GUI.
        """
        if self._current_metrics is None:
            return
        
        # Limpiar consola (multiplataforma)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 60)
        print(" PROJECT MONITOR - System Resource Monitor")
        print("=" * 60)
        print(f" Last Update: {self._current_metrics['read_time']}")
        print("-" * 60)
        
        # CPU Info
        cpu = self._current_metrics['cpu']
        print(f"\n [CPU]")
        print(f"   Total Usage: {cpu['total_percent']:.1f}%")
        print(f"   Cores: {cpu['core_count']} physical, {cpu['logical_count']} logical")
        if cpu['frequency']:
            print(f"   Frequency: {cpu['frequency']['current']:.0f} MHz")
        
        # Mostrar uso por núcleo (primeros 8 para no saturar la consola)
        cores_to_show = min(8, len(cpu['per_core_percent']))
        core_usage = " | ".join([f"C{i}:{p:.0f}%" for i, p in 
                                  enumerate(cpu['per_core_percent'][:cores_to_show])])
        print(f"   Per Core: {core_usage}")
        
        # RAM Info
        ram = self._current_metrics['ram']
        print(f"\n [RAM]")
        print(f"   Used: {self._format_bytes(ram['used'])} / {self._format_bytes(ram['total'])}")
        print(f"   Available: {self._format_bytes(ram['available'])}")
        print(f"   Usage: {ram['percent']:.1f}%")
        print(f"   Fragmentation: {ram['fragmentation']*100:.1f}% (simulated)")
        
        # Storage Info
        storage = self._current_metrics['storage']
        print(f"\n [STORAGE]")
        for partition in storage['partitions'][:3]:  # Mostrar primeras 3 particiones
            print(f"   {partition['mountpoint']}: {partition['percent']:.1f}% used "
                  f"({self._format_bytes(partition['used'])} / {self._format_bytes(partition['total'])})")
            print(f"      Fragmentation: {partition['fragmentation']*100:.1f}% (simulated)")
        
        # Network Info
        network = self._current_metrics['network']
        print(f"\n [NETWORK]")
        print(f"   Upload Speed: {self._format_bytes(network['upload_speed'])}/s")
        print(f"   Download Speed: {self._format_bytes(network['download_speed'])}/s")
        print(f"   Total Sent: {self._format_bytes(network['total_bytes_sent'])}")
        print(f"   Total Received: {self._format_bytes(network['total_bytes_recv'])}")
        
        # History Info
        print(f"\n [HISTORY]")
        print(f"   Data points stored: {len(self._metrics_history)}")
        print(f"   History duration: {len(self._metrics_history) * self.UPDATE_INTERVAL:.0f}s")
        
        print("\n" + "=" * 60)
        print(" Press Ctrl+C to stop monitoring")
        print("=" * 60)
    
    @staticmethod
    def _format_bytes(bytes_value: float) -> str:
        """
        Formatea un valor en bytes a una representación legible.
        
        Args:
            bytes_value: Valor en bytes.
        
        Returns:
            String formateado (ej: "1.5 GB", "256 MB").
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(bytes_value) < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    def start_monitoring(self) -> None:
        """
        Inicia el monitoreo del sistema.
        
        Utiliza el ThreadManager para ejecutar update_metrics()
        cada UPDATE_INTERVAL segundos.
        """
        if self._is_monitoring:
            print("[AppController] Monitoring already active.")
            return
        
        # Iniciar el hilo de recolección de datos
        success = self._thread_manager.start_data_collection_thread(
            callback=self.update_metrics,
            interval=self.UPDATE_INTERVAL,
            thread_name="system_monitor"
        )
        
        if success:
            self._is_monitoring = True
            print("[AppController] Monitoring started.")
    
    def stop_monitoring(self) -> None:
        """
        Detiene el monitoreo del sistema.
        """
        if not self._is_monitoring:
            print("[AppController] Monitoring is not active.")
            return
        
        # Detener el hilo de recolección
        self._thread_manager.stop_thread("system_monitor")
        self._is_monitoring = False
        print("[AppController] Monitoring stopped.")
    
    def get_current_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene las métricas más recientes.
        
        Returns:
            Diccionario con las métricas actuales o None si no hay datos.
        """
        return self._current_metrics
    
    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de métricas.
        
        Returns:
            Lista con el historial de métricas (hasta 1 hora).
        """
        return list(self._metrics_history)
    
    def get_process_list(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de procesos del sistema.
        
        Args:
            **kwargs: Argumentos para ProcessManager.get_process_list()
        
        Returns:
            Lista de procesos.
        """
        return self._process_manager.get_process_list(**kwargs)
    
    def kill_process(self, pid: int, force: bool = False) -> Dict[str, Any]:
        """
        Termina un proceso dado su PID.
        
        Args:
            pid: ID del proceso a terminar.
            force: Si True, usa terminación forzada.
        
        Returns:
            Resultado de la operación.
        """
        return self._process_manager.kill_process(pid, force)
    
    def search_process(self, name: str) -> List[Dict[str, Any]]:
        """
        Busca procesos por nombre.
        
        Args:
            name: Nombre del proceso a buscar.
        
        Returns:
            Lista de procesos que coinciden.
        """
        return self._process_manager.search_process_by_name(name)
    
    def is_monitoring(self) -> bool:
        """
        Verifica si el monitoreo está activo.
        
        Returns:
            True si el monitoreo está activo.
        """
        return self._is_monitoring
    
    def cleanup(self) -> None:
        """
        Limpia recursos y detiene hilos.
        
        Debe llamarse antes de cerrar la aplicación.
        """
        print("[AppController] Cleaning up...")
        self.stop_monitoring()
        self._thread_manager.stop_all_threads()
        print("[AppController] Cleanup complete.")
