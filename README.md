# Project Monitor

## Descripción

Sistema de monitoreo de recursos del sistema operativo multiplataforma (enfocado en Linux), similar a un administrador de tareas. Utiliza la arquitectura Modelo-Vista-Controlador (MVC) para una separación clara de responsabilidades.

## Características

- **Monitoreo de CPU**: Uso total y por núcleo
- **Monitoreo de RAM**: Uso total, disponible y porcentaje
- **Monitoreo de Almacenamiento**: Uso por partición
- **Monitoreo de Red**: Bytes enviados y recibidos
- **Gestión de Procesos**: Listado y terminación de procesos
- **Actualización Asíncrona**: Uso de hilos para actualización en tiempo real
- **Interfaz Gráfica**: GUI en PySide6 con resumen, alertas y tabla de procesos
- **Gráficas en tiempo real**: CPU/RAM (%) y red (upload/download) usando QtCharts
- **Filtros y control de procesos**: Búsqueda, ordenación y confirmación de terminación
- **Configuración externa**: Intervalos y umbrales ajustables vía `config.json`
- **Extras**: Cálculo de fragmentación de RAM (/proc/buddyinfo) y disco (e4defrag, cuando esté disponible), IO por proceso y selector de ventana temporal (5/15/60 min)
*- Tema*: soporta `dark` o `light` configurable en `config.json`
- **Módulos tipo Dragon Center**: térmicos (CPU/GPU), ventiladores (pwm experimental), perfiles de energía (gobernor), RGB opcional (OpenRGB), perfiles por app
- **MSI-EC**: control de fan_mode, shift_mode, Cooler Boost, umbrales de carga de batería, webcam y luz de teclado (vía sysfs, con pkexec opcional)

## Estructura del Proyecto

```
project-monitor/
├── requirements.txt
├── README.md
├── src/
│   ├── main.py              # Entrada consola
│   ├── gui_main.py          # Entrada GUI (PySide6)
│   ├── model/
│   │   ├── system_data.py
│   │   └── process_manager.py
│   ├── controller/
│   │   ├── app_controller.py
│   │   └── thread_manager.py
│   └── view/
│       ├── __init__.py
│       └── main_window.py
```

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
# Modo consola
python src/main.py

# Modo GUI (PySide6)
python src/gui_main.py
```

## Requisitos

- Python 3.x
- psutil >= 5.9.0
- PySide6 >= 6.6

## Arquitectura

El proyecto implementa el patrón MVC:

- **Model (model/)**: Clases para recopilación de datos del sistema
  - `SystemData`: Métricas de CPU, RAM, Disco y Red
  - `ProcessManager`: Gestión de procesos del sistema

- **Controller (controller/)**: Lógica de control y coordinación
  - `AppController`: Controlador principal de la aplicación
  - `ThreadManager`: Gestión de hilos para actualización asíncrona

- **View (view/)**: Interfaz gráfica de usuario en PySide6
  - `MonitorWindow`: Ventana principal con resumen, gráficas y procesos

## Configuración

Opcionalmente, crea `config.json` en la raíz del proyecto para sobreescribir valores:

```json
{
  "update_interval": 2.0,
  "history_duration": 3600,
  "process_refresh_interval": 5.0,
  "process_list_limit": 50,
  "alerts": {
    "cpu_warn": 85.0,
    "cpu_crit": 95.0,
    "ram_warn": 85.0,
    "ram_crit": 95.0
  },
  "theme": "dark",
  "rgb_enabled": false,
  "power_profiles": {
    "Silencioso": { "governor": "powersave" },
    "Equilibrado": { "governor": "schedutil" },
    "Rendimiento": { "governor": "performance" }
  },
  "profiles": {
    "juego": { "governor": "performance" },
    "bajo_consumo": { "governor": "powersave" }
  }
}
```

## Licencia

MIT License
