"""
thread_manager.py - Módulo de Gestión de Hilos

Este módulo contiene la clase ThreadManager que maneja la ejecución
asíncrona de tareas de recolección de datos utilizando threading.

Autor: Project Monitor Team
"""

import threading
import time
from typing import Callable, Optional


class ThreadManager:
    """
    Clase para gestionar hilos de ejecución para tareas asíncronas.
    
    Permite iniciar hilos daemon que ejecutan callbacks periódicamente,
    ideal para la recolección de datos del sistema sin bloquear la GUI.
    """
    
    def __init__(self):
        """
        Inicializa el ThreadManager.
        """
        self._threads = {}  # Diccionario de hilos activos
        self._stop_events = {}  # Eventos para detener hilos
        self._lock = threading.Lock()  # Lock para operaciones thread-safe
    
    def start_data_collection_thread(self, 
                                      callback: Callable[[], None],
                                      interval: float = 2.0,
                                      thread_name: str = "data_collection") -> bool:
        """
        Inicia un hilo de recolección de datos que ejecuta un callback periódicamente.
        
        Args:
            callback: Función a ejecutar periódicamente (sin argumentos).
            interval: Intervalo en segundos entre cada ejecución del callback.
            thread_name: Nombre identificador del hilo.
        
        Returns:
            True si el hilo se inició exitosamente, False si ya existe un hilo
            con ese nombre.
        """
        with self._lock:
            # Verificar si ya existe un hilo con ese nombre
            if thread_name in self._threads and self._threads[thread_name].is_alive():
                print(f"[ThreadManager] Thread '{thread_name}' already running.")
                return False
            
            # Crear evento de parada para este hilo
            stop_event = threading.Event()
            self._stop_events[thread_name] = stop_event
            
            # Crear el hilo daemon
            thread = threading.Thread(
                target=self._collection_worker,
                args=(callback, interval, stop_event),
                name=thread_name,
                daemon=True  # El hilo se cerrará cuando el programa principal termine
            )
            
            self._threads[thread_name] = thread
            thread.start()
            
            print(f"[ThreadManager] Thread '{thread_name}' started with interval {interval}s.")
            return True
    
    def _collection_worker(self, 
                           callback: Callable[[], None], 
                           interval: float,
                           stop_event: threading.Event) -> None:
        """
        Worker interno que ejecuta el callback periódicamente.
        
        Args:
            callback: Función a ejecutar.
            interval: Intervalo entre ejecuciones.
            stop_event: Evento para señalar la parada del hilo.
        """
        while not stop_event.is_set():
            try:
                # Ejecutar el callback
                callback()
            except Exception as e:
                print(f"[ThreadManager] Error in callback: {e}")
            
            # Esperar el intervalo o hasta que se señale la parada
            # Usar wait() permite responder rápidamente a la señal de parada
            stop_event.wait(timeout=interval)
    
    def stop_thread(self, thread_name: str, timeout: float = 5.0) -> bool:
        """
        Detiene un hilo de forma limpia.
        
        Args:
            thread_name: Nombre del hilo a detener.
            timeout: Tiempo máximo de espera para que el hilo termine.
        
        Returns:
            True si el hilo se detuvo exitosamente, False en caso contrario.
        """
        with self._lock:
            if thread_name not in self._threads:
                print(f"[ThreadManager] Thread '{thread_name}' not found.")
                return False
            
            thread = self._threads[thread_name]
            stop_event = self._stop_events.get(thread_name)
            
            if not thread.is_alive():
                print(f"[ThreadManager] Thread '{thread_name}' is not running.")
                return True
            
            # Señalar al hilo que debe detenerse
            if stop_event:
                stop_event.set()
            
            # Esperar a que el hilo termine
            thread.join(timeout=timeout)
            
            if thread.is_alive():
                print(f"[ThreadManager] Thread '{thread_name}' did not stop within timeout.")
                return False
            
            print(f"[ThreadManager] Thread '{thread_name}' stopped successfully.")
            return True
    
    def stop_all_threads(self, timeout: float = 5.0) -> None:
        """
        Detiene todos los hilos activos de forma limpia.
        
        Args:
            timeout: Tiempo máximo de espera para que cada hilo termine.
        """
        thread_names = list(self._threads.keys())
        
        for thread_name in thread_names:
            self.stop_thread(thread_name, timeout)
    
    def is_thread_running(self, thread_name: str) -> bool:
        """
        Verifica si un hilo está actualmente en ejecución.
        
        Args:
            thread_name: Nombre del hilo a verificar.
        
        Returns:
            True si el hilo está activo, False en caso contrario.
        """
        with self._lock:
            if thread_name not in self._threads:
                return False
            return self._threads[thread_name].is_alive()
    
    def get_active_threads(self) -> list:
        """
        Obtiene la lista de nombres de hilos activos.
        
        Returns:
            Lista de nombres de hilos que están actualmente ejecutándose.
        """
        with self._lock:
            return [name for name, thread in self._threads.items() if thread.is_alive()]
    
    def restart_thread(self, 
                       thread_name: str,
                       callback: Callable[[], None],
                       interval: float = 2.0) -> bool:
        """
        Reinicia un hilo detenido o crea uno nuevo.
        
        Args:
            thread_name: Nombre del hilo.
            callback: Función a ejecutar periódicamente.
            interval: Intervalo entre ejecuciones.
        
        Returns:
            True si el hilo se reinició exitosamente.
        """
        # Primero detener el hilo si está corriendo
        self.stop_thread(thread_name)
        
        # Iniciar nuevo hilo
        return self.start_data_collection_thread(callback, interval, thread_name)
    
    def __del__(self):
        """
        Destructor que asegura que todos los hilos se detengan.
        """
        self.stop_all_threads()
