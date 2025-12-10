"""
process_manager.py - Módulo de Gestión de Procesos

Este módulo contiene la clase ProcessManager que utiliza psutil para
listar y gestionar procesos del sistema operativo.

Autor: Project Monitor Team
"""

import psutil
from typing import Dict, List, Any, Optional


class ProcessManager:
    """
    Clase para gestionar procesos del sistema utilizando psutil.
    
    Proporciona métodos para:
    - Listar procesos activos con su información
    - Terminar procesos dado su PID
    """
    
    def __init__(self):
        """
        Inicializa la clase ProcessManager.
        """
        pass
    
    def get_process_list(self, sort_by: str = 'cpu_percent', 
                         descending: bool = True,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtiene el listado de procesos activos en el sistema.
        
        Args:
            sort_by: Campo por el cual ordenar ('cpu_percent', 'memory_percent', 
                    'pid', 'name'). Por defecto 'cpu_percent'.
            descending: Si True, ordena de mayor a menor. Por defecto True.
            limit: Número máximo de procesos a retornar. None para todos.
        
        Returns:
            Lista de diccionarios con información de cada proceso:
                - pid: ID del proceso
                - name: Nombre del proceso
                - status: Estado del proceso
                - memory_percent: Porcentaje de memoria RAM usada
                - cpu_percent: Porcentaje de CPU usada
                - username: Usuario propietario del proceso
                - create_time: Tiempo de creación del proceso
                - num_threads: Número de hilos del proceso
        """
        processes = []
        
        # Iterar sobre todos los procesos
        for proc in psutil.process_iter(['pid', 'name', 'status', 'memory_percent', 
                                          'cpu_percent', 'username', 'create_time',
                                          'num_threads', 'memory_info']):
            try:
                # Obtener información del proceso
                proc_info = proc.info
                io_counters = None
                try:
                    io_counters = proc.io_counters()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    io_counters = None
                
                process_data = {
                    'pid': proc_info['pid'],
                    'name': proc_info['name'] or 'Unknown',
                    'status': proc_info['status'] or 'Unknown',
                    'memory_percent': round(proc_info['memory_percent'] or 0, 2),
                    'cpu_percent': round(proc_info['cpu_percent'] or 0, 2),
                    'username': proc_info['username'] or 'Unknown',
                    'create_time': proc_info['create_time'],
                    'num_threads': proc_info['num_threads'] or 0,
                    'rss_bytes': proc_info.get('memory_info').rss if proc_info.get('memory_info') else 0,
                    'vms_bytes': proc_info.get('memory_info').vms if proc_info.get('memory_info') else 0,
                    'io_read_bytes': io_counters.read_bytes if io_counters else 0,
                    'io_write_bytes': io_counters.write_bytes if io_counters else 0,
                }
                
                processes.append(process_data)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # El proceso ya no existe, no tenemos acceso, o es zombie
                continue
        
        # Ordenar la lista de procesos
        if sort_by in ['cpu_percent', 'memory_percent', 'pid', 'num_threads']:
            processes.sort(key=lambda x: x.get(sort_by, 0), reverse=descending)
        elif sort_by == 'name':
            processes.sort(key=lambda x: x.get('name', '').lower(), reverse=descending)
        
        # Limitar resultados si se especifica
        if limit is not None:
            processes = processes[:limit]
        
        return processes
    
    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene información detallada de un proceso específico.
        
        Args:
            pid: ID del proceso a consultar.
        
        Returns:
            Diccionario con información detallada del proceso, o None si no existe.
        """
        try:
            proc = psutil.Process(pid)
            
            with proc.oneshot():
                return {
                    'pid': proc.pid,
                    'name': proc.name(),
                    'status': proc.status(),
                    'memory_percent': round(proc.memory_percent(), 2),
                    'memory_info': {
                        'rss': proc.memory_info().rss,  # Resident Set Size
                        'vms': proc.memory_info().vms   # Virtual Memory Size
                    },
                    'cpu_percent': round(proc.cpu_percent(interval=0.1), 2),
                    'cpu_times': {
                        'user': proc.cpu_times().user,
                        'system': proc.cpu_times().system
                    },
                    'username': proc.username(),
                    'create_time': proc.create_time(),
                    'num_threads': proc.num_threads(),
                    'exe': proc.exe() if proc.exe() else None,
                    'cmdline': proc.cmdline(),
                    'cwd': proc.cwd() if hasattr(proc, 'cwd') else None,
                    'nice': proc.nice(),
                    'ppid': proc.ppid()  # Parent PID
                }
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
    
    def kill_process(self, pid: int, force: bool = False) -> Dict[str, Any]:
        """
        Termina un proceso dado su PID.
        
        Args:
            pid: ID del proceso a terminar.
            force: Si True, usa SIGKILL (forzado). Si False, usa SIGTERM (graceful).
        
        Returns:
            Diccionario con el resultado de la operación:
                - success: True si el proceso fue terminado exitosamente
                - message: Mensaje descriptivo del resultado
                - pid: PID del proceso
        """
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
            
            if force:
                # Terminar forzadamente (SIGKILL en Linux)
                proc.kill()
                action = "killed (SIGKILL)"
            else:
                # Terminar gracefully (SIGTERM en Linux)
                proc.terminate()
                action = "terminated (SIGTERM)"
            
            # Esperar un poco para que el proceso termine
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                # Si no termina en 3 segundos con SIGTERM, informar
                if not force:
                    return {
                        'success': False,
                        'message': f"Process '{proc_name}' (PID: {pid}) did not terminate gracefully. Try with force=True.",
                        'pid': pid
                    }
            
            return {
                'success': True,
                'message': f"Process '{proc_name}' (PID: {pid}) was {action} successfully.",
                'pid': pid
            }
            
        except psutil.NoSuchProcess:
            return {
                'success': False,
                'message': f"Process with PID {pid} does not exist.",
                'pid': pid
            }
        except psutil.AccessDenied:
            return {
                'success': False,
                'message': f"Access denied. Cannot terminate process with PID {pid}. Try running with elevated privileges.",
                'pid': pid
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error terminating process with PID {pid}: {str(e)}",
                'pid': pid
            }
    
    def get_process_count(self) -> Dict[str, int]:
        """
        Obtiene el conteo de procesos por estado.
        
        Returns:
            Diccionario con el conteo de procesos por estado.
        """
        status_count = {}
        total = 0
        
        for proc in psutil.process_iter(['status']):
            try:
                status = proc.info['status']
                status_count[status] = status_count.get(status, 0) + 1
                total += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        status_count['total'] = total
        return status_count
    
    def search_process_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Busca procesos por nombre (búsqueda parcial, case-insensitive).
        
        Args:
            name: Nombre o parte del nombre del proceso a buscar.
        
        Returns:
            Lista de procesos que coinciden con el criterio de búsqueda.
        """
        matching_processes = []
        search_term = name.lower()
        
        for proc in psutil.process_iter(['pid', 'name', 'status', 'memory_percent', 'cpu_percent']):
            try:
                proc_name = proc.info['name']
                if proc_name and search_term in proc_name.lower():
                    matching_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc_name,
                        'status': proc.info['status'],
                        'memory_percent': round(proc.info['memory_percent'] or 0, 2),
                        'cpu_percent': round(proc.info['cpu_percent'] or 0, 2)
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return matching_processes
