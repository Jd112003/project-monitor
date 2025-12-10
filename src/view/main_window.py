"""
main_window.py - Ventana principal de la aplicación de monitoreo.

Implementa una interfaz sencilla con PySide6 que muestra métricas de CPU, RAM,
disco, red y una tabla básica de procesos. Se conecta al AppController mediante
un callback thread-safe usando señales Qt.
"""

import math
from typing import Dict, Any, Optional, List, Tuple

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QPieSeries


class MonitorWindow(QtWidgets.QMainWindow):
    """
    Ventana principal de la GUI del monitor.
    """

    def __init__(self, controller, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._controller = controller
        self._config = config or {}
        self._alerts = self._config.get("alerts", {})
        self._theme = str(self._config.get("theme", "dark")).lower()
        self._colors = {}
        self._last_storage: Dict[str, Any] = {}
        self._init_charts()
        self._build_ui()
        self._setup_process_refresh_timer()
        self._setup_aux_refresh_timer()

    def _build_ui(self) -> None:
        self.setWindowTitle("Project Monitor - Desktop")
        self.resize(1100, 720)
        self._apply_style()

        central = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        self.statusBar().showMessage("Esperando métricas...")

        tab = QtWidgets.QTabWidget()
        tab.setTabPosition(QtWidgets.QTabWidget.North)
        tab.setMovable(False)

        # --- Dashboard ---
        dashboard_page = QtWidgets.QWidget()
        dashboard_layout = QtWidgets.QVBoxLayout(dashboard_page)
        dashboard_layout.setContentsMargins(6, 6, 6, 6)
        dashboard_layout.setSpacing(8)

        overview_group = QtWidgets.QGroupBox("Resumen")
        overview_layout = QtWidgets.QGridLayout(overview_group)
        overview_layout.setHorizontalSpacing(16)
        overview_layout.setVerticalSpacing(8)

        # CPU
        self.cpu_progress = QtWidgets.QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_label = QtWidgets.QLabel("Cores: - | Freq: -")
        overview_layout.addWidget(QtWidgets.QLabel("CPU"), 0, 0)
        overview_layout.addWidget(self.cpu_progress, 0, 1)
        overview_layout.addWidget(self.cpu_label, 0, 2)

        # RAM
        self.ram_progress = QtWidgets.QProgressBar()
        self.ram_progress.setRange(0, 100)
        self.ram_label = QtWidgets.QLabel("Uso: - / -")
        overview_layout.addWidget(QtWidgets.QLabel("RAM"), 1, 0)
        overview_layout.addWidget(self.ram_progress, 1, 1)
        overview_layout.addWidget(self.ram_label, 1, 2)

        # Disco (primeras particiones)
        self.storage_label = QtWidgets.QLabel("Disco: -")
        overview_layout.addWidget(QtWidgets.QLabel("Disco"), 2, 0)
        overview_layout.addWidget(self.storage_label, 2, 1, 1, 2)

        # Red
        self.network_label = QtWidgets.QLabel("Red: -")
        overview_layout.addWidget(QtWidgets.QLabel("Red"), 3, 0)
        overview_layout.addWidget(self.network_label, 3, 1, 1, 2)

        # Historial
        self.history_label = QtWidgets.QLabel("Historial: -")
        overview_layout.addWidget(QtWidgets.QLabel("Historial"), 4, 0)
        overview_layout.addWidget(self.history_label, 4, 1, 1, 2)
        self.alert_label = QtWidgets.QLabel("")
        overview_layout.addWidget(self.alert_label, 5, 0, 1, 3)

        dashboard_layout.addWidget(overview_group)

        # Sección de gráficas
        charts_group = QtWidgets.QGroupBox("Tendencias recientes")
        charts_layout = QtWidgets.QVBoxLayout(charts_group)
        charts_layout.setSpacing(8)

        window_selector_layout = QtWidgets.QHBoxLayout()
        window_selector_layout.addWidget(QtWidgets.QLabel("Ventana:"))
        self.window_selector = QtWidgets.QComboBox()
        self.window_selector.addItems(["5 min", "15 min", "60 min"])
        self.window_selector.setCurrentIndex(0)
        window_selector_layout.addWidget(self.window_selector)
        window_selector_layout.addStretch()
        charts_layout.addLayout(window_selector_layout)

        charts_row = QtWidgets.QHBoxLayout()
        charts_row.setSpacing(10)
        charts_row.addWidget(self.cpu_chart_view)
        charts_row.addWidget(self.net_chart_view)
        charts_layout.addLayout(charts_row)

        dashboard_layout.addWidget(charts_group)
        tab.addTab(dashboard_page, "Dashboard")

        # Tabla de procesos
        processes_group = QtWidgets.QGroupBox("Procesos (ordenados por CPU)")
        processes_layout = QtWidgets.QVBoxLayout(processes_group)

        toolbar_layout = QtWidgets.QHBoxLayout()
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Filtrar por nombre (Enter para aplicar)")
        self.refresh_process_btn = QtWidgets.QPushButton("Refrescar")
        self.kill_process_btn = QtWidgets.QPushButton("Terminar proceso")
        self.kill_process_btn.setEnabled(False)
        toolbar_layout.addWidget(self.search_input, stretch=1)
        toolbar_layout.addWidget(self.refresh_process_btn)
        toolbar_layout.addWidget(self.kill_process_btn)
        toolbar_layout.addStretch()
        processes_layout.addLayout(toolbar_layout)

        self.process_table = QtWidgets.QTableWidget(0, 9)
        self.process_table.setHorizontalHeaderLabels(
            ["PID", "Nombre", "CPU %", "RAM %", "RSS", "IO Lect", "IO Escr", "Hilos", "Usuario"]
        )
        header = self.process_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        header.setDefaultAlignment(QtCore.Qt.AlignLeft)
        self.process_table.setSortingEnabled(True)
        self.process_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.process_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        processes_layout.addWidget(self.process_table)

        processes_page = QtWidgets.QWidget()
        processes_page_layout = QtWidgets.QVBoxLayout(processes_page)
        processes_page_layout.setContentsMargins(6, 6, 6, 6)
        processes_page_layout.setSpacing(8)
        processes_page_layout.addWidget(processes_group)
        tab.addTab(processes_page, "Procesos")

        # Panel térmico y GPU
        thermals_group = QtWidgets.QGroupBox("Térmicos y GPU")
        thermals_layout = QtWidgets.QGridLayout(thermals_group)
        thermals_layout.setHorizontalSpacing(16)
        thermals_layout.setVerticalSpacing(6)
        self.temp_list = QtWidgets.QListWidget()
        self.fan_list = QtWidgets.QListWidget()
        self.gpu_list = QtWidgets.QListWidget()
        thermals_layout.addWidget(QtWidgets.QLabel("Temperaturas"), 0, 0)
        thermals_layout.addWidget(self.temp_list, 1, 0)
        thermals_layout.addWidget(QtWidgets.QLabel("Ventiladores"), 0, 1)
        thermals_layout.addWidget(self.fan_list, 1, 1)
        thermals_layout.addWidget(QtWidgets.QLabel("GPU"), 0, 2)
        thermals_layout.addWidget(self.gpu_list, 1, 2)
        thermals_page = QtWidgets.QWidget()
        thermals_page_layout = QtWidgets.QVBoxLayout(thermals_page)
        thermals_page_layout.setContentsMargins(6, 6, 6, 6)
        thermals_page_layout.setSpacing(8)
        thermals_page_layout.addWidget(thermals_group)
        tab.addTab(thermals_page, "Térmicos / GPU")

        # Panel de energía
        power_group = QtWidgets.QGroupBox("Perfiles de energía")
        power_layout = QtWidgets.QVBoxLayout(power_group)
        self.power_status_label = QtWidgets.QLabel("Gobernador: -")
        power_layout.addWidget(self.power_status_label)
        self.power_profiles_combo = QtWidgets.QComboBox()
        self.power_profiles_combo.addItem("Selecciona un perfil")
        for name in self._config.get("power_profiles", {}).keys():
            self.power_profiles_combo.addItem(name)
        power_buttons_layout = QtWidgets.QHBoxLayout()
        self.apply_power_btn = QtWidgets.QPushButton("Aplicar perfil")
        power_buttons_layout.addWidget(self.power_profiles_combo)
        power_buttons_layout.addWidget(self.apply_power_btn)
        power_layout.addLayout(power_buttons_layout)
        # Panel de ventiladores (pwm)
        fans_group = QtWidgets.QGroupBox("Control de ventiladores (experimental)")
        fans_layout = QtWidgets.QHBoxLayout(fans_group)
        self.fan_pwm_combo = QtWidgets.QComboBox()
        self.fan_pwm_combo.addItem("Selecciona fan PWM")
        self.fan_pwm_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.fan_pwm_slider.setRange(0, 255)
        self.fan_pwm_slider.setValue(128)
        self.apply_pwm_btn = QtWidgets.QPushButton("Aplicar PWM")
        fans_layout.addWidget(self.fan_pwm_combo, 2)
        fans_layout.addWidget(self.fan_pwm_slider, 4)
        fans_layout.addWidget(self.apply_pwm_btn, 1)

        # Panel RGB
        rgb_group = QtWidgets.QGroupBox("Iluminación RGB (OpenRGB)")
        rgb_layout = QtWidgets.QHBoxLayout(rgb_group)
        self.rgb_status = QtWidgets.QLabel("Estado: no detectado")
        self.rgb_off_btn = QtWidgets.QPushButton("Apagar")
        self.rgb_static_btn = QtWidgets.QPushButton("Estático")
        self.rgb_rainbow_btn = QtWidgets.QPushButton("Arcoíris")
        rgb_layout.addWidget(self.rgb_status, 2)
        rgb_layout.addWidget(self.rgb_off_btn)
        rgb_layout.addWidget(self.rgb_static_btn)
        rgb_layout.addWidget(self.rgb_rainbow_btn)

        # Panel perfiles por app
        profiles_group = QtWidgets.QGroupBox("Perfiles por aplicación")
        profiles_layout = QtWidgets.QHBoxLayout(profiles_group)
        self.app_profile_combo = QtWidgets.QComboBox()
        self.app_profile_combo.addItem("Selecciona perfil")
        for name in self._config.get("profiles", {}).keys():
            self.app_profile_combo.addItem(name)
        self.apply_app_profile_btn = QtWidgets.QPushButton("Aplicar perfil manual")
        profiles_layout.addWidget(self.app_profile_combo, 2)
        profiles_layout.addWidget(self.apply_app_profile_btn)

        # Panel MSI-EC
        msi_group = QtWidgets.QGroupBox("MSI EC")
        msi_layout = QtWidgets.QGridLayout(msi_group)
        msi_layout.setHorizontalSpacing(8)
        msi_layout.setVerticalSpacing(6)
        self.msi_status_label = QtWidgets.QLabel("MSI-EC no detectado")
        self.msi_fan_combo = QtWidgets.QComboBox()
        self.msi_shift_combo = QtWidgets.QComboBox()
        self.msi_apply_fan_btn = QtWidgets.QPushButton("Aplicar fan mode")
        self.msi_apply_shift_btn = QtWidgets.QPushButton("Aplicar shift mode")
        self.msi_cooler_on_btn = QtWidgets.QPushButton("Cooler Boost ON")
        self.msi_cooler_off_btn = QtWidgets.QPushButton("Cooler Boost OFF")
        # batería
        self.msi_bat_start = QtWidgets.QSpinBox()
        self.msi_bat_start.setRange(0, 100)
        self.msi_bat_end = QtWidgets.QSpinBox()
        self.msi_bat_end.setRange(0, 100)
        self.msi_apply_bat_btn = QtWidgets.QPushButton("Aplicar thresholds batería")
        # webcam
        self.msi_webcam_checkbox = QtWidgets.QCheckBox("Webcam")
        self.msi_webcam_block_checkbox = QtWidgets.QCheckBox("Bloqueo webcam")
        # teclado
        self.kbd_backlight_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.kbd_backlight_slider.setRange(0, 3)
        self.kbd_backlight_slider.setTickInterval(1)
        self.kbd_backlight_label = QtWidgets.QLabel("Luz teclado")
        self.kbd_apply_btn = QtWidgets.QPushButton("Aplicar luz teclado")
        # Auto-aplica el brillo tras una breve pausa para evitar múltiples escrituras
        self._kbd_backlight_sync = False
        self._kbd_apply_timer = QtCore.QTimer(self)
        self._kbd_apply_timer.setSingleShot(True)

        msi_layout.addWidget(self.msi_status_label, 0, 0, 1, 4)
        msi_layout.addWidget(QtWidgets.QLabel("Fan mode"), 1, 0)
        msi_layout.addWidget(self.msi_fan_combo, 1, 1)
        msi_layout.addWidget(self.msi_apply_fan_btn, 1, 2)
        msi_layout.addWidget(QtWidgets.QLabel("Shift mode"), 2, 0)
        msi_layout.addWidget(self.msi_shift_combo, 2, 1)
        msi_layout.addWidget(self.msi_apply_shift_btn, 2, 2)
        msi_layout.addWidget(self.msi_cooler_on_btn, 3, 0)
        msi_layout.addWidget(self.msi_cooler_off_btn, 3, 1)
        msi_layout.addWidget(QtWidgets.QLabel("Batería start/end"), 4, 0)
        msi_layout.addWidget(self.msi_bat_start, 4, 1)
        msi_layout.addWidget(self.msi_bat_end, 4, 2)
        msi_layout.addWidget(self.msi_apply_bat_btn, 4, 3)
        msi_layout.addWidget(self.msi_webcam_checkbox, 5, 0)
        msi_layout.addWidget(self.msi_webcam_block_checkbox, 5, 1)
        msi_layout.addWidget(self.kbd_backlight_label, 6, 0)
        msi_layout.addWidget(self.kbd_backlight_slider, 6, 1, 1, 2)
        msi_layout.addWidget(self.kbd_apply_btn, 6, 3)

        control_page = QtWidgets.QWidget()
        control_layout = QtWidgets.QVBoxLayout(control_page)
        control_layout.setContentsMargins(6, 6, 6, 6)
        control_layout.setSpacing(8)
        control_layout.addWidget(power_group)
        control_layout.addWidget(fans_group)
        control_layout.addWidget(rgb_group)
        control_layout.addWidget(profiles_group)
        control_layout.addWidget(msi_group)
        tab.addTab(control_page, "Control")

        # Pestaña de fragmentación
        frag_page = QtWidgets.QWidget()
        frag_layout = QtWidgets.QVBoxLayout(frag_page)
        frag_layout.setContentsMargins(6, 6, 6, 6)
        frag_layout.setSpacing(8)

        frag_header = QtWidgets.QHBoxLayout()
        self.frag_refresh_btn = QtWidgets.QPushButton("Refrescar fragmentación")
        frag_header.addWidget(self.frag_refresh_btn)
        frag_header.addStretch()
        self.frag_hint_label = QtWidgets.QLabel("Colores según fragmentación (verde=ok, rojo=muy fragmentado). Si no hay dato de fragmentación, se usa el % de uso para colorear.")
        self.frag_hint_label.setWordWrap(True)
        frag_header.addWidget(self.frag_hint_label)
        frag_layout.addLayout(frag_header)

        self.frag_table = QtWidgets.QTableWidget(0, 5)
        self.frag_table.setHorizontalHeaderLabels(["Mount", "FS", "Uso", "% usado", "Frag"])
        frag_header_widget = self.frag_table.horizontalHeader()
        frag_header_widget.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        frag_header_widget.setDefaultAlignment(QtCore.Qt.AlignLeft)
        self.frag_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.frag_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        frag_layout.addWidget(self.frag_table)

        frag_toggle_layout = QtWidgets.QHBoxLayout()
        frag_toggle_layout.addStretch()
        self.frag_rings_btn = QtWidgets.QPushButton("Rings Chart")
        self.frag_treemap_btn = QtWidgets.QPushButton("Treemap Chart")
        self.frag_rings_btn.setCheckable(True)
        self.frag_treemap_btn.setCheckable(True)
        self.frag_chart_group = QtWidgets.QButtonGroup(self)
        self.frag_chart_group.setExclusive(True)
        self.frag_chart_group.addButton(self.frag_rings_btn, 0)
        self.frag_chart_group.addButton(self.frag_treemap_btn, 1)
        frag_toggle_layout.addWidget(self.frag_rings_btn)
        frag_toggle_layout.addWidget(self.frag_treemap_btn)
        frag_layout.addLayout(frag_toggle_layout)

        self.frag_stack = QtWidgets.QStackedWidget()
        self.frag_stack.addWidget(self.frag_ring_view)
        self.frag_stack.addWidget(self.frag_treemap)
        self.frag_stack.setCurrentIndex(0)
        frag_layout.addWidget(self.frag_stack, 1)

        tab.addTab(frag_page, "Fragmentación")

        main_layout.addWidget(tab)
        self.setCentralWidget(central)

        # Conexiones
        self.refresh_process_btn.clicked.connect(self.refresh_process_table)
        self.kill_process_btn.clicked.connect(self._kill_selected_process)
        self.process_table.itemSelectionChanged.connect(self._on_process_selection)
        self.search_input.returnPressed.connect(self.refresh_process_table)
        self.window_selector.currentIndexChanged.connect(self._refresh_charts_from_history)
        self.apply_power_btn.clicked.connect(self._apply_power_profile)
        self.apply_pwm_btn.clicked.connect(self._apply_pwm)
        self.rgb_off_btn.clicked.connect(lambda: self._apply_rgb("off"))
        self.rgb_static_btn.clicked.connect(lambda: self._apply_rgb("static"))
        self.rgb_rainbow_btn.clicked.connect(lambda: self._apply_rgb("rainbow"))
        self.apply_app_profile_btn.clicked.connect(self._apply_app_profile)
        self.msi_apply_fan_btn.clicked.connect(self._apply_msi_fan_mode)
        self.msi_apply_shift_btn.clicked.connect(self._apply_msi_shift_mode)
        self.msi_cooler_on_btn.clicked.connect(lambda: self._set_msi_cooler_boost("on"))
        self.msi_cooler_off_btn.clicked.connect(lambda: self._set_msi_cooler_boost("off"))
        self.msi_apply_bat_btn.clicked.connect(self._apply_msi_battery_thresholds)
        self.msi_webcam_checkbox.stateChanged.connect(self._toggle_msi_webcam)
        self.msi_webcam_block_checkbox.stateChanged.connect(self._toggle_msi_webcam_block)
        self.kbd_backlight_slider.valueChanged.connect(self._on_kbd_backlight_changed)
        self._kbd_apply_timer.timeout.connect(lambda: self._apply_kbd_backlight(show_dialog=False))
        self.kbd_apply_btn.clicked.connect(lambda: self._apply_kbd_backlight())
        self.frag_refresh_btn.clicked.connect(self._refresh_fragmentation_tab)
        self.frag_rings_btn.clicked.connect(lambda: self._set_frag_chart_mode(0))
        self.frag_treemap_btn.clicked.connect(lambda: self._set_frag_chart_mode(1))
        self.frag_rings_btn.setChecked(True)

    def _init_charts(self) -> None:
        """Inicializa objetos de gráficas y ejes."""
        # Series
        self.cpu_series = QLineSeries(name="CPU %")
        self.ram_series = QLineSeries(name="RAM %")
        self.cpu_series.setColor(QtGui.QColor("#5DA9E9"))
        self.ram_series.setColor(QtGui.QColor("#8CD17D"))

        self.net_up_series = QLineSeries(name="Upload")
        self.net_down_series = QLineSeries(name="Download")
        self.net_up_series.setColor(QtGui.QColor("#E39C45"))
        self.net_down_series.setColor(QtGui.QColor("#C065D8"))

        # Chart CPU/RAM
        self.cpu_chart = QChart()
        self.cpu_chart.setTitle("CPU y RAM (%) - últimos minutos")
        self.cpu_chart.addSeries(self.cpu_series)
        self.cpu_chart.addSeries(self.ram_series)
        self.cpu_x_axis = QValueAxis()
        self.cpu_x_axis.setTitleText("Tiempo (s)")
        self.cpu_y_axis = QValueAxis()
        self.cpu_y_axis.setRange(0, 100)
        self.cpu_y_axis.setTitleText("Porcentaje")
        for axis, align in ((self.cpu_x_axis, QtCore.Qt.AlignBottom), (self.cpu_y_axis, QtCore.Qt.AlignLeft)):
            self.cpu_chart.addAxis(axis, align)
        for series in (self.cpu_series, self.ram_series):
            series.attachAxis(self.cpu_x_axis)
            series.attachAxis(self.cpu_y_axis)
        self.cpu_chart.legend().setVisible(True)
        self.cpu_chart.legend().setAlignment(QtCore.Qt.AlignBottom)
        self.cpu_chart_view = QChartView(self.cpu_chart)
        self.cpu_chart_view.setRenderHint(QtGui.QPainter.Antialiasing)

        # Chart red
        self.net_chart = QChart()
        self.net_chart.setTitle("Red (bytes/s) - últimos minutos")
        self.net_chart.addSeries(self.net_up_series)
        self.net_chart.addSeries(self.net_down_series)
        self.net_x_axis = QValueAxis()
        self.net_x_axis.setTitleText("Tiempo (s)")
        self.net_y_axis = QValueAxis()
        self.net_y_axis.setRange(0, 1)
        self.net_y_axis.setTitleText("Velocidad (bytes/s)")
        for axis, align in ((self.net_x_axis, QtCore.Qt.AlignBottom), (self.net_y_axis, QtCore.Qt.AlignLeft)):
            self.net_chart.addAxis(axis, align)
        for series in (self.net_up_series, self.net_down_series):
            series.attachAxis(self.net_x_axis)
            series.attachAxis(self.net_y_axis)
        self.net_chart.legend().setVisible(True)
        self.net_chart.legend().setAlignment(QtCore.Qt.AlignBottom)
        self.net_chart_view = QChartView(self.net_chart)
        self.net_chart_view.setRenderHint(QtGui.QPainter.Antialiasing)

        theme = QChart.ChartThemeLight if self._theme == "light" else QChart.ChartThemeDark
        self.cpu_chart.setTheme(theme)
        self.net_chart.setTheme(theme)
        self._init_fragmentation_charts()

    def _init_fragmentation_charts(self) -> None:
        """Inicializa widgets para la pestaña de fragmentación."""
        self.frag_ring_chart = QChart()
        self.frag_ring_chart.setTitle("Uso por partición (color = fragmentación)")
        self.frag_ring_chart.legend().setVisible(True)
        self.frag_ring_chart.legend().setAlignment(QtCore.Qt.AlignRight)
        self.frag_ring_view = QChartView(self.frag_ring_chart)
        self.frag_ring_view.setRenderHint(QtGui.QPainter.Antialiasing)

        self.frag_treemap = FragmentationTreemap()

    def _apply_style(self) -> None:
        """Aplica el estilo según el tema configurado."""
        if self._theme == "light":
            self._colors = {
                "bg": "#F3F4F6",
                "text": "#111827",
                "group_border": "#D1D5DB",
                "group_title": "#2563EB",
                "progress_bg": "#E5E7EB",
                "button_bg": "#E5E7EB",
                "button_hover": "#D1D5DB",
                "button_border": "#D1D5DB",
                "table_bg": "#FFFFFF",
                "table_grid": "#E5E7EB",
                "table_selection": "#DBEAFE",
                "header_bg": "#E5E7EB",
                "status_bg": "#E5E7EB",
                "status_text": "#111827",
            }
        else:
            self._colors = {
                "bg": "#111827",
                "text": "#E4E7F1",
                "group_border": "#243047",
                "group_title": "#A5B4FC",
                "progress_bg": "#0B1220",
                "button_bg": "#1F2A3E",
                "button_hover": "#243047",
                "button_border": "#243047",
                "table_bg": "#0B1220",
                "table_grid": "#1F2A3E",
                "table_selection": "#243B53",
                "header_bg": "#1F2A3E",
                "status_bg": "#0B1220",
                "status_text": "#A5B4FC",
            }

        self.setStyleSheet(
            f"""
            QWidget {{ font-family: 'Segoe UI', 'Noto Sans', sans-serif; color: {self._colors['text']}; background: {self._colors['bg']}; }}
            QGroupBox {{ border: 1px solid {self._colors['group_border']}; border-radius: 8px; margin-top: 8px; padding: 8px 10px 10px 10px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {self._colors['group_title']}; font-weight: 600; }}
            QProgressBar {{ border: 1px solid {self._colors['group_border']}; border-radius: 6px; background: {self._colors['progress_bg']}; height: 20px; }}
            QProgressBar::chunk {{ background-color: #5DA9E9; border-radius: 6px; }}
            QPushButton {{ background: {self._colors['button_bg']}; border: 1px solid {self._colors['button_border']}; border-radius: 6px; padding: 6px 12px; color: {self._colors['text']}; }}
            QPushButton:hover {{ background: {self._colors['button_hover']}; }}
            QTableWidget {{ background: {self._colors['table_bg']}; gridline-color: {self._colors['table_grid']}; selection-background-color: {self._colors['table_selection']}; }}
            QHeaderView::section {{ background: {self._colors['header_bg']}; padding: 6px; border: none; }}
            QStatusBar {{ background: {self._colors['status_bg']}; color: {self._colors['status_text']}; }}
            """
        )
        theme = QChart.ChartThemeLight if self._theme == "light" else QChart.ChartThemeDark
        self.frag_ring_chart.setTheme(theme)
        self.frag_treemap.set_colors(
            bg=self._colors.get("table_bg", self._colors["bg"]),
            text=self._colors["text"],
            border=self._colors.get("group_border", "#243047"),
        )

    def _setup_process_refresh_timer(self) -> None:
        """Refresca la tabla de procesos periódicamente."""
        interval = float(self._config.get("process_refresh_interval", 5.0)) * 1000
        self._process_timer = QtCore.QTimer(self)
        self._process_timer.timeout.connect(self.refresh_process_table)
        self._process_timer.start(int(interval))

    def _setup_aux_refresh_timer(self) -> None:
        """Refresca datos térmicos, GPU y energía periódicamente."""
        self._aux_timer = QtCore.QTimer(self)
        self._aux_timer.timeout.connect(self._refresh_aux_panels)
        self._aux_timer.start(2000)

    @QtCore.Slot(dict)
    def handle_metrics(self, metrics: Dict[str, Any]) -> None:
        """Actualiza la UI con nuevas métricas."""
        cpu = metrics.get("cpu", {})
        ram = metrics.get("ram", {})
        storage = metrics.get("storage", {})
        network = metrics.get("network", {})
        self._last_storage = storage or {}

        cpu_percent = float(cpu.get("total_percent", 0))
        self.cpu_progress.setValue(int(cpu_percent))
        self.cpu_progress.setFormat(f"{cpu_percent:.1f}%")
        self.cpu_label.setText(
            f"Cores: {cpu.get('core_count', '-')}/{cpu.get('logical_count', '-')}"
            f" | Freq: {self._safe_freq(cpu.get('frequency'))}"
        )

        ram_percent = float(ram.get("percent", 0))
        self.ram_progress.setValue(int(ram_percent))
        self.ram_progress.setFormat(f"{ram_percent:.1f}%")
        frag = ram.get("fragmentation")
        frag_text = f" | Frag: {frag*100:.1f}%" if frag is not None else ""
        self.ram_label.setText(
            f"{self._format_bytes(ram.get('used', 0))} / {self._format_bytes(ram.get('total', 0))}{frag_text}"
        )

        partitions = storage.get("partitions", [])
        if partitions:
            parts = []
            for p in partitions[:3]:
                frag = p.get("fragmentation")
                frag_s = f", frag {frag*100:.1f}%" if frag is not None else ""
                parts.append(f"{p.get('mountpoint', '?')}: {p.get('percent', 0):.1f}%{frag_s}")
            parts_text = " | ".join(parts)
        else:
            parts_text = "Sin datos de particiones"
        self.storage_label.setText(parts_text)

        upload = self._format_speed(network.get("upload_speed", 0))
        download = self._format_speed(network.get("download_speed", 0))
        self.network_label.setText(f"Up: {upload} | Down: {download}")

        history_count = len(self._controller.get_metrics_history())
        self.history_label.setText(
            f"Datos: {history_count} | Última lectura: {metrics.get('read_time', '-')}"
        )
        self._update_fragmentation_tab(self._last_storage)

        self.statusBar().showMessage("Métricas actualizadas")
        self._refresh_charts_from_history()
        self._apply_alerts(cpu_percent, ram_percent)
        # Refrescar paneles auxiliares cerca del pulso de métricas
        self._refresh_thermals()
        self._refresh_gpu()
        # Refrescar paneles auxiliares menos frecuentemente
        # (el timer dedicado los actualizará también)

    def refresh_process_table(self) -> None:
        """Solicita la lista de procesos y refresca la tabla."""
        try:
            search_term = self.search_input.text().strip().lower()
            processes = self._controller.get_process_list(sort_by="cpu_percent", limit=self._config.get("process_list_limit"))
            if search_term:
                processes = [p for p in processes if search_term in str(p.get("name", "")).lower()]
        except Exception as exc:
            self.statusBar().showMessage(f"Error al obtener procesos: {exc}")
            return

        self.process_table.setRowCount(len(processes))

        columns = [
            ("pid", False),
            ("name", False),
            ("cpu_percent", True),
            ("memory_percent", True),
            ("rss_bytes", True),
            ("io_read_bytes", True),
            ("io_write_bytes", True),
            ("num_threads", True),
            ("username", False),
        ]

        for row, proc in enumerate(processes):
            for col, (key, is_numeric) in enumerate(columns):
                value = proc.get(key, "")
                if key in ("rss_bytes", "io_read_bytes", "io_write_bytes"):
                    value = self._format_bytes(value)
                item = QtWidgets.QTableWidgetItem(str(value))
                if is_numeric:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.process_table.setItem(row, col, item)

        self.kill_process_btn.setEnabled(False)
        self.statusBar().showMessage("Procesos actualizados")

    def _kill_selected_process(self) -> None:
        """Termina el proceso seleccionado en la tabla."""
        row = self.process_table.currentRow()
        if row < 0:
            return
        pid_item = self.process_table.item(row, 0)
        if not pid_item:
            return
        pid = int(pid_item.text())
        result = self._controller.kill_process(pid, force=False)
        if not result.get("success"):
            choice = QtWidgets.QMessageBox.question(
                self,
                "Forzar terminación",
                f"{result.get('message', '')}\n\n¿Forzar con SIGKILL?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if choice == QtWidgets.QMessageBox.Yes:
                result = self._controller.kill_process(pid, force=True)

        QtWidgets.QMessageBox.information(self, "Resultado", result.get("message", ""))
        self.refresh_process_table()

    def _on_process_selection(self) -> None:
        self.kill_process_btn.setEnabled(self.process_table.currentRow() >= 0)

    def closeEvent(self, event) -> None:  # noqa: N802
        """Detiene el monitoreo al cerrar la ventana."""
        try:
            self._controller.cleanup()
        finally:
            super().closeEvent(event)

    def _refresh_charts_from_history(self) -> None:
        """Actualiza series de gráficas a partir del historial reciente."""
        history = self._controller.get_metrics_history()
        if not history:
            return

        window_seconds = self._selected_window_seconds()
        latest_ts = history[-1]["timestamp"]
        recent = [h for h in history if h["timestamp"] >= latest_ts - window_seconds]
        if not recent:
            return

        base_time = recent[0]["timestamp"]

        cpu_points = []
        ram_points = []
        up_points = []
        down_points = []

        for entry in recent:
            x = entry["timestamp"] - base_time
            cpu_points.append((x, entry.get("cpu_percent", 0)))
            ram_points.append((x, entry.get("ram_percent", 0)))
            up_points.append((x, entry.get("network_upload", 0)))
            down_points.append((x, entry.get("network_download", 0)))

        self._set_series_points(self.cpu_series, cpu_points)
        self._set_series_points(self.ram_series, ram_points)
        self._set_series_points(self.net_up_series, up_points)
        self._set_series_points(self.net_down_series, down_points)

        max_x = max((p[0] for p in cpu_points), default=60.0)
        self.cpu_x_axis.setRange(0, max_x or 60.0)
        self.net_x_axis.setRange(0, max_x or 60.0)

        self.cpu_y_axis.setRange(0, 100)

        max_net = max(
            [p[1] for p in up_points] + [p[1] for p in down_points] + [1]
        )
        self.net_y_axis.setRange(0, max_net * 1.2)

    def _selected_window_seconds(self) -> float:
        """Devuelve la ventana temporal elegida en segundos."""
        mapping = {0: 300, 1: 900, 2: 3600}
        return float(mapping.get(self.window_selector.currentIndex(), 300))

    def _refresh_aux_panels(self) -> None:
        """Actualiza paneles de sensores, GPU, energía, batería y fan PWM."""
        self._refresh_thermals()
        self._refresh_gpu()
        self._refresh_power()
        self._refresh_rgb_status()
        self._refresh_fan_pwm_options()
        self._refresh_msi_ec()

    def _refresh_thermals(self) -> None:
        temps = self._controller.get_temperatures()
        self.temp_list.clear()
        for name, entries in temps.items():
            for entry in entries:
                line = f"{entry['label']} {entry['current']:.1f}°C"
                self.temp_list.addItem(line)

        fans = self._controller.get_fans()
        self.fan_list.clear()
        if not fans:
            self.fan_list.addItem("No se detectaron ventiladores")
        else:
            for fan in fans:
                rpm = fan.get("rpm") or 0
                line = f"{fan.get('label', 'fan')} - {rpm}"
                if fan.get("source") == "msi-ec":
                    line += " (msi-ec)"
                else:
                    line += " RPM"
                self.fan_list.addItem(line)

        bat = self._controller.get_battery_info()
        if bat:
            plug = "AC" if bat.get("plugged") else "Batería"
            secs = bat.get("secs_left")
            remaining = f"{secs//60} min" if secs and secs > 0 else "N/A"
            self.temp_list.addItem(f"Batería: {bat.get('percent', 0):.0f}% ({plug}) {remaining}")

    def _refresh_gpu(self) -> None:
        gpus = self._controller.get_gpu_info()
        self.gpu_list.clear()
        if not gpus:
            self.gpu_list.addItem("Sin GPU detectada o comandos no disponibles")
            return
        for gpu in gpus:
            line = (
                f"{gpu.get('vendor')} {gpu.get('name')} | "
                f"Uso {gpu.get('utilization', 0):.0f}% | "
                f"VRAM {gpu.get('mem_used_mb', 0):.0f}/{gpu.get('mem_total_mb', 0):.0f} MB | "
                f"T {gpu.get('temperature', 0):.0f}°C"
            )
            self.gpu_list.addItem(line)

    def _refresh_power(self) -> None:
        state = self._controller.get_power_state()
        gov = state.get("current") or "-"
        max_freq = state.get("max_freq")
        max_freq_ghz = f"{(max_freq/1_000_000):.2f} GHz" if max_freq else "-"
        self.power_status_label.setText(f"Gobernador actual: {gov} | Freq máx: {max_freq_ghz}")

    def _refresh_rgb_status(self) -> None:
        available = self._controller.rgb_available()
        self.rgb_status.setText("OpenRGB disponible" if available else "RGB no disponible")
        for btn in (self.rgb_off_btn, self.rgb_static_btn, self.rgb_rainbow_btn):
            btn.setEnabled(available)

    def _refresh_fan_pwm_options(self) -> None:
        fans = self._controller.get_fans()
        pwm_fans = [f for f in fans if f.get("pwm_path")]
        current_items = {self.fan_pwm_combo.itemText(i): i for i in range(self.fan_pwm_combo.count())}
        # Reset combo if needed
        self.fan_pwm_combo.blockSignals(True)
        self.fan_pwm_combo.clear()
        self.fan_pwm_combo.addItem("Selecciona fan PWM")
        for fan in pwm_fans:
            label = fan.get("label", "fan")
            self.fan_pwm_combo.addItem(label, fan.get("pwm_path"))
        self.fan_pwm_combo.blockSignals(False)

    def _refresh_fragmentation_tab(self) -> None:
        """Refresca los datos de fragmentación bajo demanda."""
        try:
            storage = self._controller.get_storage_snapshot()
            self._last_storage = storage or {}
            self._update_fragmentation_tab(self._last_storage)
            self.statusBar().showMessage("Fragmentación actualizada")
        except Exception as exc:
            self.statusBar().showMessage(f"Error al refrescar fragmentación: {exc}")

    def _set_frag_chart_mode(self, index: int) -> None:
        self.frag_stack.setCurrentIndex(index)
        self.frag_rings_btn.setChecked(index == 0)
        self.frag_treemap_btn.setChecked(index == 1)

    def _update_fragmentation_tab(self, storage: Dict[str, Any]) -> None:
        partitions = storage.get("partitions", []) if storage else []
        self.frag_table.setRowCount(len(partitions))
        for row, part in enumerate(partitions):
            mount = part.get("mountpoint", "?")
            fstype = part.get("fstype", "-")
            used = self._format_bytes(part.get("used", 0))
            total = self._format_bytes(part.get("total", 0))
            percent = part.get("percent", 0.0) or 0.0
            frag = part.get("fragmentation")
            frag_text = "-" if frag is None else f"{frag*100:.1f}%"

            items = [
                QtWidgets.QTableWidgetItem(mount),
                QtWidgets.QTableWidgetItem(fstype),
                QtWidgets.QTableWidgetItem(f"{used} / {total}"),
                QtWidgets.QTableWidgetItem(f"{percent:.1f}%"),
                QtWidgets.QTableWidgetItem(frag_text),
            ]
            for idx, item in enumerate(items):
                if idx >= 3:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.frag_table.setItem(row, idx, item)
            color = self._color_for_fragmentation(frag, percent)
            items[-1].setBackground(QtGui.QBrush(color))
            dark_text = frag is not None and frag > 0.6
            items[-1].setForeground(QtGui.QBrush(QtGui.QColor("#0B1220" if dark_text else self._colors.get("text", "#E4E7F1"))))

        # Gráficos
        self._populate_frag_ring_chart(partitions)
        self._populate_frag_treemap(partitions)

    def _populate_frag_ring_chart(self, partitions: List[Dict[str, Any]]) -> None:
        self.frag_ring_chart.removeAllSeries()
        series = QPieSeries()
        series.setHoleSize(0.4)

        # ordenar por uso para un colorido más claro
        sorted_parts = sorted(partitions, key=lambda p: p.get("used", 0), reverse=True)
        for part in sorted_parts:
            used = part.get("used", 0) or 0
            if used <= 0:
                continue
            frag = part.get("fragmentation")
            label = part.get("mountpoint", "?")
            frag_text = "-" if frag is None else f"{frag*100:.1f}%"
            percent = part.get("percent", 0.0) or 0.0
            slice_obj = series.append(f"{label} ({percent:.1f}%, frag {frag_text})", used)
            slice_obj.setLabelVisible(len(sorted_parts) <= 8)
            slice_obj.setColor(self._color_for_fragmentation(frag, percent))
        if not series.slices():
            series.append("Sin datos", 1)
            series.slices()[-1].setColor(QtGui.QColor(self._colors.get("group_border", "#243047")))
        self.frag_ring_chart.addSeries(series)
        self.frag_ring_chart.legend().setVisible(True)
        self.frag_ring_chart.legend().setAlignment(QtCore.Qt.AlignRight)

    def _populate_frag_treemap(self, partitions: List[Dict[str, Any]]) -> None:
        items = []
        for part in partitions:
            used = part.get("used", 0) or 0
            if used <= 0:
                continue
            items.append(
                {
                    "label": part.get("mountpoint", "?"),
                    "value": used,
                    "percent": part.get("percent", 0.0) or 0.0,
                    "frag": part.get("fragmentation"),
                    "color": self._color_for_fragmentation(part.get("fragmentation"), part.get("percent", 0.0)),
                }
            )
        self.frag_treemap.set_data(items)

    def _color_for_fragmentation(self, frag: Optional[float], pct_used: Optional[float] = None) -> QtGui.QColor:
        """Devuelve color de gradiente verde->amarillo->rojo según fragmentación.
        Si no hay fragmentación, usa un gradiente azulado según % usado."""
        if frag is None:
            if pct_used is None:
                return QtGui.QColor("#6B7280") if self._theme == "light" else QtGui.QColor("#4B5563")
            val = max(0.0, min(1.0, float(pct_used) / 100.0))
            # Azul claro a azul profundo según uso
            r = int(96 + (20 - 96) * val)
            g = int(165 + (50 - 165) * val)
            b = int(250 + (120 - 250) * val)
            return QtGui.QColor(r, g, b)
        val = max(0.0, min(1.0, float(frag)))
        # 0-0.5: verde a amarillo, 0.5-1: amarillo a rojo
        if val <= 0.5:
            t = val / 0.5
            r = int(34 + (234 - 34) * t)   # 34->234
            g = int(197 + (179 - 197) * t)  # 197->179
            b = int(94 + (8 - 94) * t)     # 94->8
        else:
            t = (val - 0.5) / 0.5
            r = int(234 + (239 - 234) * t)  # 234->239
            g = int(179 + (68 - 179) * t)   # 179->68
            b = int(8 + (68 - 8) * t)       # 8->68
        return QtGui.QColor(r, g, b)

    def _apply_power_profile(self) -> None:
        name = self.power_profiles_combo.currentText()
        if not name or name == "Selecciona un perfil":
            return
        res = self._controller.set_power_profile(name)
        QtWidgets.QMessageBox.information(self, "Perfil de energía", res.get("message", ""))
        self._refresh_power()

    def _apply_pwm(self) -> None:
        pwm_path = self.fan_pwm_combo.currentData()
        if not pwm_path:
            QtWidgets.QMessageBox.warning(self, "PWM", "Selecciona un ventilador con PWM disponible")
            return
        value = self.fan_pwm_slider.value()
        res = self._controller.set_fan_pwm(pwm_path, value)
        QtWidgets.QMessageBox.information(self, "PWM", res.get("message", ""))

    def _apply_rgb(self, preset: str) -> None:
        res = self._controller.set_rgb_preset(preset)
        QtWidgets.QMessageBox.information(self, "RGB", res.get("message", ""))

    def _apply_app_profile(self) -> None:
        name = self.app_profile_combo.currentText()
        if not name or name == "Selecciona perfil":
            return
        res = self._controller.apply_app_profile(name)
        QtWidgets.QMessageBox.information(self, "Perfil", res.get("message", ""))

    def _refresh_msi_ec(self) -> None:
        info = self._controller.get_msi_ec_info()
        if not info.get("available"):
            self.msi_status_label.setText("MSI-EC no detectado")
            self._kbd_apply_timer.stop()
            for widget in (
                self.msi_fan_combo,
                self.msi_shift_combo,
                self.msi_apply_fan_btn,
                self.msi_apply_shift_btn,
                self.msi_cooler_on_btn,
                self.msi_cooler_off_btn,
                self.msi_bat_start,
                self.msi_bat_end,
                self.msi_apply_bat_btn,
                self.msi_webcam_checkbox,
                self.msi_webcam_block_checkbox,
                self.kbd_backlight_slider,
                self.kbd_apply_btn,
            ):
                widget.setEnabled(False)
            return

        self.msi_status_label.setText(
            f"MSI-EC activo | Fan: {info.get('fan_mode','-')} | Shift: {info.get('shift_mode','-')} | CoolerBoost: {info.get('cooler_boost','-')}"
        )

        # Poblar combos
        fan_modes = info.get("available_fan_modes", [])
        shift_modes = info.get("available_shift_modes", [])
        self._fill_combo(self.msi_fan_combo, fan_modes, info.get("fan_mode"))
        self._fill_combo(self.msi_shift_combo, shift_modes, info.get("shift_mode"))

        # Batería
        bat = self._controller.get_msi_battery_info()
        if bat:
            try:
                self.msi_bat_start.setValue(int(bat.get("start_threshold") or 0))
                self.msi_bat_end.setValue(int(bat.get("end_threshold") or 0))
            except Exception:
                pass

        # Webcam
        self.msi_webcam_checkbox.blockSignals(True)
        self.msi_webcam_block_checkbox.blockSignals(True)
        self.msi_webcam_checkbox.setChecked((info.get("webcam") or "").lower() == "on")
        self.msi_webcam_block_checkbox.setChecked((info.get("webcam_block") or "").lower() == "on")
        self.msi_webcam_checkbox.blockSignals(False)
        self.msi_webcam_block_checkbox.blockSignals(False)

        # Backlight
        try:
            self._kbd_apply_timer.stop()
            self._kbd_backlight_sync = True
            current_kbd = int(self._controller.get_keyboard_backlight() or 0)
            self.kbd_backlight_slider.setValue(current_kbd)
            self._update_kbd_backlight_label(applied=True)
        except Exception:
            self._update_kbd_backlight_label(applied=True)
        finally:
            self._kbd_backlight_sync = False

        for widget in (
            self.msi_fan_combo,
            self.msi_shift_combo,
            self.msi_apply_fan_btn,
            self.msi_apply_shift_btn,
            self.msi_cooler_on_btn,
            self.msi_cooler_off_btn,
            self.msi_bat_start,
            self.msi_bat_end,
            self.msi_apply_bat_btn,
            self.msi_webcam_checkbox,
            self.msi_webcam_block_checkbox,
            self.kbd_backlight_slider,
            self.kbd_apply_btn,
        ):
            widget.setEnabled(True)

    def _fill_combo(self, combo: QtWidgets.QComboBox, options: list, current: Optional[str]) -> None:
        combo.blockSignals(True)
        combo.clear()
        for opt in options:
            combo.addItem(opt)
        if current and current in options:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _apply_msi_fan_mode(self) -> None:
        mode = self.msi_fan_combo.currentText()
        if not mode:
            return
        res = self._controller.set_msi_fan_mode(mode)
        QtWidgets.QMessageBox.information(self, "MSI-EC", res.get("message", ""))
        self._refresh_msi_ec()

    def _apply_msi_shift_mode(self) -> None:
        mode = self.msi_shift_combo.currentText()
        if not mode:
            return
        res = self._controller.set_msi_shift_mode(mode)
        QtWidgets.QMessageBox.information(self, "MSI-EC", res.get("message", ""))
        self._refresh_msi_ec()

    def _set_msi_cooler_boost(self, value: str) -> None:
        res = self._controller.set_msi_cooler_boost(value)
        QtWidgets.QMessageBox.information(self, "MSI-EC", res.get("message", ""))
        QtCore.QTimer.singleShot(1500, self._refresh_msi_ec)

    def _apply_msi_battery_thresholds(self) -> None:
        start = self.msi_bat_start.value()
        end = self.msi_bat_end.value()
        res = self._controller.set_msi_battery_thresholds(start, end)
        QtWidgets.QMessageBox.information(self, "MSI-EC", res.get("message", ""))
        self._refresh_msi_ec()

    def _toggle_msi_webcam(self, state: int) -> None:
        res = self._controller.set_msi_webcam(state == QtCore.Qt.Checked)
        QtWidgets.QMessageBox.information(self, "MSI-EC", res.get("message", ""))

    def _toggle_msi_webcam_block(self, state: int) -> None:
        res = self._controller.set_msi_webcam_block(state == QtCore.Qt.Checked)
        QtWidgets.QMessageBox.information(self, "MSI-EC", res.get("message", ""))

    def _on_kbd_backlight_changed(self, value: int) -> None:
        if self._kbd_backlight_sync:
            return
        self._update_kbd_backlight_label(applied=False)
        self._kbd_apply_timer.start(500)
        self.statusBar().showMessage(f"Luz teclado pendiente ({value})")

    def _apply_kbd_backlight(self, show_dialog: bool = True) -> None:
        self._kbd_apply_timer.stop()
        level = self.kbd_backlight_slider.value()
        res = self._controller.set_keyboard_backlight(level)
        message = res.get("message", "") or f"Luz teclado ajustada a {level}"
        if show_dialog:
            QtWidgets.QMessageBox.information(self, "MSI-EC", message)
        else:
            self.statusBar().showMessage(message)
        self._update_kbd_backlight_label(applied=True)

    def _update_kbd_backlight_label(self, applied: bool = False) -> None:
        level = self.kbd_backlight_slider.value()
        if applied:
            self.kbd_backlight_label.setText(f"Luz teclado (nivel {level})")
        else:
            self.kbd_backlight_label.setText(f"Luz teclado (pendiente: {level})")

    @staticmethod
    def _format_bytes(bytes_value: float) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(bytes_value) < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"

    @staticmethod
    def _safe_freq(freq_info: Optional[Dict[str, Any]]) -> str:
        if not freq_info:
            return "-"
        current = freq_info.get("current")
        return f"{current:.0f} MHz" if current else "-"

    @staticmethod
    def _set_series_points(series: QLineSeries, points: List[Tuple[float, float]]) -> None:
        """Reemplaza puntos de una serie de forma segura."""
        series.replace([QtCore.QPointF(x, y) for x, y in points])

    def _format_speed(self, bytes_per_sec: float) -> str:
        """Formatea velocidad en bytes/s a unidades humanas."""
        for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
            if abs(bytes_per_sec) < 1024.0:
                return f"{bytes_per_sec:.1f} {unit}"
            bytes_per_sec /= 1024.0
        return f"{bytes_per_sec:.1f} TB/s"

    def _apply_alerts(self, cpu_percent: float, ram_percent: float) -> None:
        """Aplica colores y mensajes de alerta según umbrales configurados."""
        cpu_level = self._level_for_value(cpu_percent, "cpu")
        ram_level = self._level_for_value(ram_percent, "ram")

        self._apply_bar_style(self.cpu_progress, cpu_level, default_color="#5DA9E9")
        self._apply_bar_style(self.ram_progress, ram_level, default_color="#8CD17D")

        message_parts = []
        if cpu_level == "crit":
            message_parts.append("CPU alta")
        elif cpu_level == "warn":
            message_parts.append("CPU elevada")

        if ram_level == "crit":
            message_parts.append("RAM alta")
        elif ram_level == "warn":
            message_parts.append("RAM elevada")

        text = " | ".join(message_parts) if message_parts else "Sistema dentro de rangos normales"
        self.alert_label.setText(text)

    def _level_for_value(self, value: float, key: str) -> str:
        warn = float(self._alerts.get(f"{key}_warn", 85.0))
        crit = float(self._alerts.get(f"{key}_crit", 95.0))
        if value >= crit:
            return "crit"
        if value >= warn:
            return "warn"
        return "ok"

    def _apply_bar_style(self, bar: QtWidgets.QProgressBar, level: str, default_color: str) -> None:
        colors = {"ok": default_color, "warn": "#E3B341", "crit": "#E15D5D"}
        color = colors.get(level, default_color)
        bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid {self._colors.get('group_border', '#243047')};
                border-radius: 6px;
                background: {self._colors.get('progress_bg', '#0B1220')};
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 6px;
            }}
            """
        )


class FragmentationTreemap(QtWidgets.QWidget):
    """Widget simple para mostrar un treemap de fragmentación por partición."""

    def __init__(self) -> None:
        super().__init__()
        self._items: List[Dict[str, Any]] = []
        self._bg = QtGui.QColor("#111827")
        self._text = QtGui.QColor("#E4E7F1")
        self._border = QtGui.QColor("#243047")
        self.setMinimumHeight(260)

    def set_colors(self, bg: str, text: str, border: str) -> None:
        self._bg = QtGui.QColor(bg)
        self._text = QtGui.QColor(text)
        self._border = QtGui.QColor(border)
        self.update()

    def set_data(self, items: List[Dict[str, Any]]) -> None:
        self._items = items or []
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), self._bg)

        data = [i for i in self._items if i.get("value", 0) > 0]
        if not data:
            painter.setPen(self._text)
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, "Sin datos de fragmentación")
            return

        rects = self._layout_rows(data, QtCore.QRectF(self.rect()))
        for rect, item in rects:
            color = item.get("color") or self._border
            painter.fillRect(rect.adjusted(1, 1, -1, -1), color)
            painter.setPen(QtGui.QPen(self._border, 1))
            painter.drawRect(rect.adjusted(0.5, 0.5, -0.5, -0.5))
            painter.setPen(self._text)
            frag = item.get("frag")
            frag_text = "-" if frag is None else f"{frag*100:.1f}%"
            text = f"{item.get('label', '?')} {item.get('percent', 0.0):.1f}% | Frag {frag_text}"
            painter.drawText(rect.adjusted(6, 6, -6, -6), QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, text)

    def _layout_rows(self, items: List[Dict[str, Any]], rect: QtCore.QRectF) -> List[Tuple[QtCore.QRectF, Dict[str, Any]]]:
        """Distribuye las particiones en filas proporcionadas por su peso."""
        total = sum(i.get("value", 0) for i in items)
        if total <= 0:
            return []
        rows = max(1, int(math.sqrt(len(items))))
        chunk_size = max(1, math.ceil(len(items) / rows))
        rects: List[Tuple[QtCore.QRectF, Dict[str, Any]]] = []
        y = rect.y()
        remaining_height = rect.height()
        remaining_total = total

        for idx in range(0, len(items), chunk_size):
            chunk = items[idx : idx + chunk_size]
            chunk_total = sum(i.get("value", 0) for i in chunk)
            row_height = remaining_height * (chunk_total / remaining_total) if remaining_total else 0
            x = rect.x()
            for item in chunk:
                width = rect.width() * (item.get("value", 0) / chunk_total) if chunk_total else 0
                rects.append((QtCore.QRectF(x, y, width, row_height), item))
                x += width
            y += row_height
            remaining_height -= row_height
            remaining_total -= chunk_total
        return rects
