"""
system_data.py - Módulo de Métricas Core del Sistema

Este módulo contiene la clase SystemData que utiliza psutil para obtener
métricas del sistema operativo. Diseñado para ser compatible con Linux.

Autor: Project Monitor Team
"""

import psutil
import time
import subprocess
from typing import Dict, List, Any, Optional


class SystemData:
    """
    Clase para recopilar métricas del sistema utilizando psutil.
    
    Proporciona métodos para obtener información sobre:
    - CPU (uso total y por núcleo)
    - RAM (uso total, disponible, porcentaje)
    - Almacenamiento (uso por partición)
    - Red (bytes enviados y recibidos)
    """
    
    FRAG_CACHE_TTL = 600  # segundos para reutilizar cálculo de fragmentación de disco
    
    def __init__(self):
        """
        Inicializa la clase SystemData.
        
        Guarda los valores iniciales de red para calcular deltas y caches internos.
        """
        # Almacenar valores iniciales de red para calcular diferencias
        self._last_net_io = psutil.net_io_counters()
        self._last_net_time = time.time()
        self._disk_frag_cache: Dict[str, Dict[str, Any]] = {}
    
    def get_cpu_metrics(self) -> Dict[str, Any]:
        """
        Obtiene las métricas de uso de CPU.
        
        Returns:
            Dict con:
                - total_percent: Porcentaje de uso total de CPU
                - per_core_percent: Lista con porcentaje de uso por núcleo
                - core_count: Número de núcleos físicos
                - logical_count: Número de núcleos lógicos
                - frequency: Frecuencia actual de CPU (si está disponible)
        """
        cpu_percent_total = psutil.cpu_percent(interval=0.1)
        cpu_percent_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_freq = psutil.cpu_freq()
        
        return {
            'total_percent': cpu_percent_total,
            'per_core_percent': cpu_percent_per_core,
            'core_count': psutil.cpu_count(logical=False),
            'logical_count': psutil.cpu_count(logical=True),
            'frequency': {
                'current': cpu_freq.current if cpu_freq else 0,
                'min': cpu_freq.min if cpu_freq else 0,
                'max': cpu_freq.max if cpu_freq else 0
            } if cpu_freq else None
        }
    
    def get_ram_metrics(self) -> Dict[str, Any]:
        """
        Obtiene las métricas de uso de RAM.
        
        Returns:
            Dict con:
                - total: Memoria total en bytes
                - available: Memoria disponible en bytes
                - used: Memoria usada en bytes
                - percent: Porcentaje de uso
                - fragmentation: Índice de fragmentación (simulado)
        """
        memory = psutil.virtual_memory()
        fragmentation = self._get_ram_fragmentation_linux()
        
        return {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'percent': memory.percent,
            'fragmentation': fragmentation,
            # Datos adicionales útiles
            'buffers': getattr(memory, 'buffers', 0),
            'cached': getattr(memory, 'cached', 0),
            'shared': getattr(memory, 'shared', 0)
        }
    
    def get_storage_metrics(self) -> Dict[str, Any]:
        """
        Obtiene las métricas de uso de almacenamiento por partición.
        
        Returns:
            Dict con:
                - partitions: Lista de diccionarios con info de cada partición
                - total_usage: Uso total agregado de todas las particiones
        """
        partitions_info = []
        total_used = 0
        total_size = 0
        
        partitions = psutil.disk_partitions()
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                fragmentation = self._get_disk_fragmentation_linux(partition.mountpoint, partition.fstype)
                
                partition_data = {
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent,
                    'fragmentation': fragmentation
                }
                
                partitions_info.append(partition_data)
                total_used += usage.used
                total_size += usage.total
                
            except (PermissionError, OSError):
                # Algunas particiones pueden no ser accesibles
                continue
        
        return {
            'partitions': partitions_info,
            'total_usage': {
                'total': total_size,
                'used': total_used,
                'free': total_size - total_used,
                'percent': (total_used / total_size * 100) if total_size > 0 else 0
            }
        }
    
    def get_network_metrics(self) -> Dict[str, Any]:
        """
        Obtiene las métricas de red (bytes enviados y recibidos).
        
        Calcula la diferencia desde la última llamada para obtener
        la velocidad de transferencia en el intervalo.
        
        Returns:
            Dict con:
                - bytes_sent: Bytes enviados en el intervalo
                - bytes_recv: Bytes recibidos en el intervalo
                - total_bytes_sent: Total acumulado de bytes enviados
                - total_bytes_recv: Total acumulado de bytes recibidos
                - upload_speed: Velocidad de subida en bytes/segundo
                - download_speed: Velocidad de bajada en bytes/segundo
        """
        current_net_io = psutil.net_io_counters()
        current_time = time.time()
        
        # Calcular el tiempo transcurrido
        time_delta = current_time - self._last_net_time
        
        # Calcular bytes transferidos en el intervalo
        bytes_sent_delta = current_net_io.bytes_sent - self._last_net_io.bytes_sent
        bytes_recv_delta = current_net_io.bytes_recv - self._last_net_io.bytes_recv
        
        # Calcular velocidades (bytes por segundo)
        upload_speed = bytes_sent_delta / time_delta if time_delta > 0 else 0
        download_speed = bytes_recv_delta / time_delta if time_delta > 0 else 0
        
        # Actualizar valores para la próxima llamada
        self._last_net_io = current_net_io
        self._last_net_time = current_time
        
        return {
            'bytes_sent': bytes_sent_delta,
            'bytes_recv': bytes_recv_delta,
            'total_bytes_sent': current_net_io.bytes_sent,
            'total_bytes_recv': current_net_io.bytes_recv,
            'upload_speed': upload_speed,
            'download_speed': download_speed,
            'packets_sent': current_net_io.packets_sent,
            'packets_recv': current_net_io.packets_recv,
            'errin': current_net_io.errin,
            'errout': current_net_io.errout
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Obtiene todas las métricas del sistema en una sola llamada.
        
        Returns:
            Dict con todas las métricas: cpu, ram, storage, network
        """
        return {
            'cpu': self.get_cpu_metrics(),
            'ram': self.get_ram_metrics(),
            'storage': self.get_storage_metrics(),
            'network': self.get_network_metrics(),
            'timestamp': time.time()
        }

    def _get_ram_fragmentation_linux(self) -> Optional[float]:
        """
        Calcula un índice simple de fragmentación de RAM a partir de /proc/buddyinfo.
        Valor entre 0 (sin fragmentación) y 1 (alta fragmentación). None si no aplica.
        """
        try:
            with open("/proc/buddyinfo", "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return None
        except Exception:
            return None

        total_pages = 0
        largest_block_pages = 0

        for line in lines:
            parts = line.strip().split()
            # Formato: Node 0, zone   DMA  1 2 3 4 ... (contadores por orden)
            counts = [int(x) for x in parts[4:]]  # los primeros 4 tokens son cabecera
            for order, count in enumerate(counts):
                pages = (2 ** order)
                total_pages += count * pages
                if count > 0:
                    largest_block_pages = max(largest_block_pages, pages)

        if total_pages == 0:
            return None

        fragmentation_index = 1.0 - (largest_block_pages / total_pages)
        return max(0.0, min(fragmentation_index, 1.0))

    def _get_disk_fragmentation_linux(self, mountpoint: str, fstype: str) -> Optional[float]:
        """
        Intenta obtener un puntaje de fragmentación para sistemas ext basados en e4defrag.
        Devuelve None si no es soportado o si falla la medición.
        """
        # Cachear resultados para evitar costo en cada lectura
        cached = self._disk_frag_cache.get(mountpoint)
        now = time.time()
        if cached and (now - cached.get("ts", 0) < self.FRAG_CACHE_TTL):
            return cached.get("value")

        if not fstype.startswith("ext"):
            return None

        try:
            result = subprocess.run(
                ["e4defrag", "-c", mountpoint],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            output = result.stdout or result.stderr
            score = None
            for line in output.splitlines():
                if "Fragmentation score" in line:
                    # ejemplo: Fragmentation score : 12
                    try:
                        score_str = line.split(":")[1].strip().split()[0]
                        score = float(score_str)
                        break
                    except Exception:
                        continue

            if score is not None:
                # Normalizar a 0-1 asumiendo 0-100 como rango típico
                normalized = max(0.0, min(score / 100.0, 1.0))
            else:
                normalized = None
        except (FileNotFoundError, subprocess.SubprocessError):
            normalized = None

        self._disk_frag_cache[mountpoint] = {"ts": now, "value": normalized}
        return normalized
