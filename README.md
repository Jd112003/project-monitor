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

## Estructura del Proyecto

```
project-monitor/
├── requirements.txt
├── README.md
├── src/
│   ├── main.py
│   ├── model/
│   │   ├── system_data.py
│   │   └── process_manager.py
│   └── controller/
│       ├── app_controller.py
│       └── thread_manager.py
```

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
python src/main.py
```

## Requisitos

- Python 3.x
- psutil >= 5.9.0

## Arquitectura

El proyecto implementa el patrón MVC:

- **Model (model/)**: Clases para recopilación de datos del sistema
  - `SystemData`: Métricas de CPU, RAM, Disco y Red
  - `ProcessManager`: Gestión de procesos del sistema

- **Controller (controller/)**: Lógica de control y coordinación
  - `AppController`: Controlador principal de la aplicación
  - `ThreadManager`: Gestión de hilos para actualización asíncrona

- **View**: (Por implementar) Interfaz gráfica de usuario

## Licencia

MIT License
