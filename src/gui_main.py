"""
Entrada de la aplicación GUI usando PySide6.

Lanza la ventana principal y conecta el AppController a través de señales Qt
para recibir métricas desde el hilo de monitoreo sin bloquear la UI.
"""

import sys

from PySide6 import QtCore, QtWidgets

from controller.app_controller import AppController
from view.main_window import MonitorWindow
from config import load_config


class MetricsBridge(QtCore.QObject):
    """Puente de señales entre el hilo de métricas y el hilo de la GUI."""

    metrics_updated = QtCore.Signal(dict)


def main():
    app = QtWidgets.QApplication(sys.argv)

    config = load_config()
    controller = AppController(
        update_interval=config.get("update_interval"),
        history_duration=config.get("history_duration"),
        config=config,
    )
    bridge = MetricsBridge()

    window = MonitorWindow(controller, config)
    bridge.metrics_updated.connect(window.handle_metrics)
    controller.set_view_callback(bridge.metrics_updated.emit)

    controller.start_monitoring()
    app.aboutToQuit.connect(controller.cleanup)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
