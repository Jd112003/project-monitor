"""
main.py - Punto de Entrada de la Aplicación

Este módulo es el punto de entrada principal del sistema de monitoreo.
Inicializa el controlador y comienza el ciclo de monitoreo.

Autor: Project Monitor Team
"""

import sys
import signal
import time

# Importar el controlador principal
from controller.app_controller import AppController


def signal_handler(signum, frame):
    """
    Manejador de señales para cierre limpio de la aplicación.
    
    Args:
        signum: Número de señal recibida.
        frame: Frame de ejecución actual.
    """
    print("\n\n[Main] Interrupt signal received. Shutting down...")
    global controller
    if controller:
        controller.cleanup()
    sys.exit(0)


# Variable global para el controlador (necesaria para el signal handler)
controller = None


def main():
    """
    Función principal de la aplicación.
    
    Inicializa el controlador y ejecuta el ciclo de monitoreo.
    """
    global controller
    
    print("=" * 60)
    print(" PROJECT MONITOR - System Resource Monitor")
    print(" Initializing...")
    print("=" * 60)
    
    # Registrar manejadores de señales para cierre limpio
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Crear instancia del controlador
        controller = AppController()
        
        # Iniciar el monitoreo
        controller.start_monitoring()
        
        # Mantener el programa en ejecución
        # En una implementación con GUI, aquí se iniciaría el main loop de la GUI
        # Por ahora, simplemente esperamos indefinidamente
        print("[Main] Monitoring active. Press Ctrl+C to stop.\n")
        
        while True:
            # El hilo de monitoreo se ejecuta en background
            # Este loop mantiene vivo el programa principal
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n[Main] Keyboard interrupt received.")
    except Exception as e:
        print(f"\n[Main] Error: {e}")
    finally:
        if controller:
            controller.cleanup()
        print("[Main] Application terminated.")


if __name__ == "__main__":
    main()
