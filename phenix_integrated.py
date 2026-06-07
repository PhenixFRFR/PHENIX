import sys
import os
import cv2
import math
import random
import subprocess
import numpy as np
import folium
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ThermalSimulator:
    def __init__(self, width=320, height=240):
        self.width = width
        self.height = height
        self.survivors = []

    def add_survivor(self, x, y, temp=37.0):
        self.survivors.append({'x': x, 'y': y, 'temp': temp, 'id': len(self.survivors) + 1})

    def generate_frame(self):
        frame = np.zeros((self.height, self.width), dtype=np.float32)
        frame += np.random.normal(20, 2, frame.shape).astype(np.float32)
        for survivor in self.survivors:
            x, y = int(survivor['x']), int(survivor['y'])
            temp = survivor['temp'] + random.uniform(-0.5, 0.5)
            for dy in range(-15, 16):
                for dx in range(-15, 16):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        dist = math.sqrt(dx**2 + dy**2)
                        heat = temp * math.exp(-dist**2 / 50)
                        frame[ny, nx] = max(frame[ny, nx], heat)
        return frame

    def detect_survivors(self, frame, threshold=35.0):
        detected = []
        hot_mask = (frame > threshold).astype(np.uint8)
        contours, _ = cv2.findContours(hot_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            if cv2.contourArea(contour) > 10:
                M = cv2.moments(contour)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    max_temp = float(np.max(frame[hot_mask > 0]))
                    detected.append({
                        'x': cx, 'y': cy,
                        'temp': max_temp,
                        'confidence': min(100, int((max_temp - threshold) * 10))
                    })
        return detected


class RSSIGraph(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(4, 2), facecolor='#1a1a2e')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#0a0a1a')
        self.ax.tick_params(colors='#00ff88')
        for spine in self.ax.spines.values():
            spine.set_color('#00ff88')
        super().__init__(self.fig)
        self.rssi_data = []

    def update_graph(self, rssi):
        self.rssi_data.append(rssi)
        if len(self.rssi_data) > 60:
            self.rssi_data.pop(0)
        self.ax.clear()
        self.ax.set_facecolor('#0a0a1a')
        self.ax.set_ylim(-120, -40)
        self.ax.set_title('RSSI履歴', color='#00ff88', fontsize=9)
        self.ax.tick_params(colors='#00ff88')
        for spine in self.ax.spines.values():
            spine.set_color('#00ff88')
        self.ax.axhline(y=-85, color='#ff4444', linestyle='--')
        colors = ['#ff4444' if r < -85 else '#00ff88' for r in self.rssi_data]
        self.ax.bar(range(len(self.rssi_data)), self.rssi_data, color=colors, alpha=0.7)
        self.draw()


class PHENIXIntegrated(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔥 PHENIX 統合システム v4.0")
        self.setGeometry(50, 50, 1600, 950)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        # システム状態
        self.node_count = 8
        self.countdown_value = 0
        self.current_mode = "待機中"
        self.emergency = False
        self.auto_return_enabled = True
        self.auto_return_triggered = False
        self.manual_mode = False
        self.obstacle_detected = False
        self.circle_radius = 100
        self.follow_altitude = 30
        self.nodes = []
        self.survivors_detected = []
        self.base_lat = -33.2833
        self.base_lng = 149.1000
        self.mother_pos = [self.base_lat, self.base_lng]
        self.drone_pos = [self.base_lat + 0.001, self.base_lng + 0.001]
        self.map_file = os.path.expanduser("~/PHENIX/integrated_map.html")

        # サーマル
        self.thermal = ThermalSimulator()
        self.thermal.add_survivor(160, 120, 37.5)
        self.thermal.add_survivor(80, 180, 36.8)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # タイトル
        title = QLabel("🔥 PHENIX 統合システム v4.0")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # 接続状態
        self.connection_status = QLabel("🔗 MAVLink: 接続中 | LoRa: 待機中 | DB: 稼働中 | サーマル: 待機中")
        self.connection_status.setStyleSheet("font-size: 11px; color: #00aaff;")
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.connection_status)

        # メインコンテンツ
        content_layout = QHBoxLayout()

        # 左パネル
        left_panel = QWidget()
        left_panel.setMaximumWidth(380)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(5)

        # 操作ボタン
        control_group = QGroupBox("🎮 操作パネル")
        control_group.setStyleSheet("QGroupBox { color: #00ff88; border: 2px solid #00ff88; padding: 3px; font-size: 12px; }")
        control_layout = QGridLayout()

        buttons = [
            ("🟢 追従", "#00ff88", 0, 0, self.start_follow),
            ("🔴 解除", "#ff4444", 0, 1, self.stop_follow),
            ("🔵 旋回", "#00aaff", 0, 2, self.start_circle),
            ("🟡 帰還", "#ffaa00", 1, 0, self.start_return),
            ("⛔ 緊急停止", "#ff0000", 1, 1, self.emergency_stop),
            ("🚀 ノード投下", "#ff66ff", 1, 2, self.drop_node),
        ]

        for text, color, row, col, func in buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #111122;
                    color: {color};
                    border: 2px solid {color};
                    padding: 8px;
                    font-size: 12px;
                    border-radius: 4px;
                }}
                QPushButton:hover {{ background-color: #222244; }}
                QPushButton:pressed {{ background-color: {color}; color: #000000; }}
            """)
            btn.clicked.connect(func)
            control_layout.addWidget(btn, row, col)

        # 手動/自動切り替え
        self.btn_manual = QPushButton("🤖 自動モード")
        self.btn_manual.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                color: #00ff88;
                border: 2px solid #00ff88;
                padding: 8px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #005500; }
        """)
        self.btn_manual.clicked.connect(self.toggle_manual)
        control_layout.addWidget(self.btn_manual, 2, 0, 1, 2)

        # 自動帰還トグル
        self.btn_auto_return = QPushButton("🔒 自動帰還: ON")
        self.btn_auto_return.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                color: #00ff88;
                border: 2px solid #00ff88;
                padding: 8px;
                font-size: 12px;
                border-radius: 4px;
            }
        """)
        self.btn_auto_return.clicked.connect(self.toggle_auto_return)
        control_layout.addWidget(self.btn_auto_return, 2, 2)

        control_group.setLayout(control_layout)
        left_layout.addWidget(control_group)

        # スライダー
        slider_group = QGroupBox("⚙️ パラメーター")
        slider_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 3px; font-size: 12px; }")
        slider_layout = QGridLayout()

        slider_layout.addWidget(QLabel("旋回半径:"), 0, 0)
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setMinimum(1)
        self.radius_slider.setMaximum(1000)
        self.radius_slider.setValue(100)
        self.radius_slider.valueChanged.connect(lambda v: self.radius_label.setText(f"{v}m"))
        slider_layout.addWidget(self.radius_slider, 0, 1)
        self.radius_label = QLabel("100m")
        self.radius_label.setStyleSheet("color: #00aaff;")
        slider_layout.addWidget(self.radius_label, 0, 2)

        slider_layout.addWidget(QLabel("追従高度:"), 1, 0)
        self.altitude_slider = QSlider(Qt.Orientation.Horizontal)
        self.altitude_slider.setMinimum(1)
        self.altitude_slider.setMaximum(500)
        self.altitude_slider.setValue(30)
        self.altitude_slider.valueChanged.connect(lambda v: self.altitude_label.setText(f"{v}m"))
        slider_layout.addWidget(self.altitude_slider, 1, 1)
        self.altitude_label = QLabel("30m")
        self.altitude_label.setStyleSheet("color: #00ff88;")
        slider_layout.addWidget(self.altitude_label, 1, 2)

        slider_group.setLayout(slider_layout)
        left_layout.addWidget(slider_group)

        # 現在のモード
        self.mode_label = QLabel("現在のモード: 待機中")
        self.mode_label.setStyleSheet("font-size: 14px; color: #ffaa00; font-weight: bold;")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.mode_label)

        # 障害物検知表示
        self.obstacle_label = QLabel("✅ 障害物なし")
        self.obstacle_label.setStyleSheet("font-size: 13px; color: #00ff88;")
        self.obstacle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.obstacle_label)

        # LoRa通信
        lora_group = QGroupBox("📡 LoRa通信")
        lora_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 3px; font-size: 12px; }")
        lora_layout = QVBoxLayout()
        self.rssi_label = QLabel("RSSI: --- dBm")
        self.rssi_label.setStyleSheet("font-size: 16px; color: #00ff88;")
        self.countdown_label = QLabel("投下まで: 待機中")
        self.countdown_label.setStyleSheet("font-size: 12px; color: #ffaa00;")
        self.node_count_label = QLabel(f"ノード残数: {self.node_count}個")
        self.node_count_label.setStyleSheet("font-size: 12px; color: #ffaa00;")
        lora_layout.addWidget(self.rssi_label)
        lora_layout.addWidget(self.countdown_label)
        lora_layout.addWidget(self.node_count_label)
        lora_group.setLayout(lora_layout)
        left_layout.addWidget(lora_group)

        # バッテリー
        battery_group = QGroupBox("🔋 バッテリー")
        battery_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 3px; font-size: 12px; }")
        battery_layout = QVBoxLayout()
        self.battery_mother = QProgressBar()
        self.battery_mother.setStyleSheet("QProgressBar::chunk { background-color: #00ff88; }")
        self.battery_drone = QProgressBar()
        self.battery_drone.setStyleSheet("QProgressBar::chunk { background-color: #00aaff; }")
        self.bat_mother_label = QLabel("母艦: 100%")
        self.bat_mother_label.setStyleSheet("color: #00ff88; font-size: 12px;")
        self.bat_drone_label = QLabel("ドローン: 100%")
        self.bat_drone_label.setStyleSheet("color: #00aaff; font-size: 12px;")
        battery_layout.addWidget(self.bat_mother_label)
        battery_layout.addWidget(self.battery_mother)
        battery_layout.addWidget(self.bat_drone_label)
        battery_layout.addWidget(self.battery_drone)
        battery_group.setLayout(battery_layout)
        left_layout.addWidget(battery_group)

        # 生存者検知
        survivor_group = QGroupBox("👤 生存者検知")
        survivor_group.setStyleSheet("QGroupBox { color: #ff4444; border: 1px solid #ff4444; padding: 3px; font-size: 12px; }")
        survivor_layout = QVBoxLayout()
        self.survivor_count = QLabel("検知数: 0人")
        self.survivor_count.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff4444;")
        survivor_layout.addWidget(self.survivor_count)
        self.survivor_coords = QLabel("座標: ---")
        self.survivor_coords.setStyleSheet("font-size: 11px; color: #ff6666;")
        survivor_layout.addWidget(self.survivor_coords)
        btn_detect = QPushButton("🌡️ サーマル検知開始")
        btn_detect.setStyleSheet("""
            QPushButton {
                background-color: #330000;
                color: #ff4444;
                border: 2px solid #ff4444;
                padding: 8px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #550000; }
        """)
        btn_detect.clicked.connect(self.toggle_thermal)
        survivor_layout.addWidget(btn_detect)
        survivor_group.setLayout(survivor_layout)
        left_layout.addWidget(survivor_group)

        # 地図ボタン
        btn_map = QPushButton("🗺️ 地図を開く")
        btn_map.setStyleSheet("""
            QPushButton {
                background-color: #003333;
                color: #00ffff;
                border: 2px solid #00ffff;
                padding: 8px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #005555; }
        """)
        btn_map.clicked.connect(self.open_map)
        left_layout.addWidget(btn_map)

        content_layout.addWidget(left_panel)

        # 中央パネル：サーマル + RSSI
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_panel.setMaximumWidth(680)

        thermal_group = QGroupBox("🌡️ サーマルカメラ映像")
        thermal_group.setStyleSheet("QGroupBox { color: #ff6666; border: 1px solid #ff6666; padding: 3px; font-size: 12px; }")
        thermal_layout = QVBoxLayout()
        self.thermal_label = QLabel()
        self.thermal_label.setFixedSize(640, 480)
        self.thermal_label.setStyleSheet("background-color: #000000;")
        self.thermal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thermal_layout.addWidget(self.thermal_label)
        thermal_group.setLayout(thermal_layout)
        center_layout.addWidget(thermal_group)

        self.rssi_graph = RSSIGraph()
        center_layout.addWidget(self.rssi_graph)

        content_layout.addWidget(center_panel)

        # 右パネル：GPS + センサー + ログ
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # GPS
        gps_group = QGroupBox("📍 GPS位置情報")
        gps_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 3px; font-size: 12px; }")
        gps_layout = QVBoxLayout()
        self.mother_gps = QLabel("母艦: ---, ---")
        self.mother_gps.setStyleSheet("font-size: 12px; color: #00ff88;")
        self.drone_gps = QLabel("ドローン: ---, ---")
        self.drone_gps.setStyleSheet("font-size: 12px; color: #00aaff;")
        gps_layout.addWidget(self.mother_gps)
        gps_layout.addWidget(self.drone_gps)
        for i in range(3):
            label = QLabel(f"ノード{i+1}: ---, ---")
            label.setStyleSheet("font-size: 11px; color: #ffaa00;")
            gps_layout.addWidget(label)
            setattr(self, f'node_gps_{i}', label)
        gps_group.setLayout(gps_layout)
        right_layout.addWidget(gps_group)

        # センサー
        sensor_group = QGroupBox("🌡️ センサーデータ")
        sensor_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 3px; font-size: 12px; }")
        sensor_layout = QVBoxLayout()
        self.temperature = QLabel("気温: --- ℃")
        self.temperature.setStyleSheet("font-size: 12px; color: #ff6666;")
        self.humidity = QLabel("湿度: --- %")
        self.humidity.setStyleSheet("font-size: 12px; color: #66aaff;")
        self.pressure_label = QLabel("気圧: --- hPa")
        self.pressure_label.setStyleSheet("font-size: 12px; color: #66ff66;")
        self.drone_alt = QLabel("高度: --- m")
        self.drone_alt.setStyleSheet("font-size: 12px; color: #00aaff;")
        self.drone_speed = QLabel("速度: --- km/h")
        self.drone_speed.setStyleSheet("font-size: 12px; color: #00aaff;")
        self.drone_heading = QLabel("方位: --- °")
        self.drone_heading.setStyleSheet("font-size: 12px; color: #aa66ff;")
        sensor_layout.addWidget(self.temperature)
        sensor_layout.addWidget(self.humidity)
        sensor_layout.addWidget(self.pressure_label)
        sensor_layout.addWidget(self.drone_alt)
        sensor_layout.addWidget(self.drone_speed)
        sensor_layout.addWidget(self.drone_heading)
        sensor_group.setLayout(sensor_layout)
        right_layout.addWidget(sensor_group)

        # アラート
        alert_group = QGroupBox("⚠️ アラート")
        alert_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 3px; font-size: 12px; }")
        alert_layout = QVBoxLayout()
        self.alert_label = QLabel("✅ 正常稼働中")
        self.alert_label.setStyleSheet("font-size: 13px; color: #00ff88;")
        alert_layout.addWidget(self.alert_label)
        alert_group.setLayout(alert_layout)
        right_layout.addWidget(alert_group)

        # ログ
        log_group = QGroupBox("📋 イベントログ")
        log_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 3px; font-size: 12px; }")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("background-color: #0a0a1a; color: #00ff88; font-family: monospace; font-size: 11px;")
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)

        content_layout.addWidget(right_panel)
        main_layout.addLayout(content_layout)

        # バッテリー初期値
        self.battery_mother.setValue(100)
        self.battery_drone.setValue(100)

        # タイマー
        self.main_timer = QTimer()
        self.main_timer.timeout.connect(self.update_display)
        self.main_timer.start(1000)

        self.thermal_timer = QTimer()
        self.thermal_timer.timeout.connect(self.update_thermal)
        self.thermal_running = False

        self.obstacle_timer = QTimer()
        self.obstacle_timer.timeout.connect(self.simulate_obstacle)
        self.obstacle_timer.start(5000)

        self.update_map()
        self.add_log("🔥 PHENIX 統合システム v4.0 起動！")
        self.add_log("✅ 全システム初期化完了")

    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def start_follow(self):
        self.current_mode = "追従モード"
        self.mode_label.setText(f"現在のモード: 🟢 追従モード（高度:{self.altitude_slider.value()}m）")
        self.mode_label.setStyleSheet("font-size: 14px; color: #00ff88; font-weight: bold;")
        self.add_log(f"🟢 追従モード開始！高度: {self.altitude_slider.value()}m")
        self.emergency = False
        self.auto_return_triggered = False

    def stop_follow(self):
        self.current_mode = "ホバリング"
        self.mode_label.setText("現在のモード: 🔴 追従解除（ホバリング）")
        self.mode_label.setStyleSheet("font-size: 14px; color: #ff4444; font-weight: bold;")
        self.add_log("🔴 追従解除！ドローンはホバリング中")

    def start_circle(self):
        self.current_mode = "旋回モード"
        self.mode_label.setText(f"現在のモード: 🔵 旋回モード（半径:{self.radius_slider.value()}m）")
        self.mode_label.setStyleSheet("font-size: 14px; color: #00aaff; font-weight: bold;")
        self.add_log(f"🔵 旋回モード開始！半径: {self.radius_slider.value()}m")

    def start_return(self):
        self.current_mode = "帰還モード"
        self.mode_label.setText("現在のモード: 🟡 帰還モード")
        self.mode_label.setStyleSheet("font-size: 14px; color: #ffaa00; font-weight: bold;")
        self.add_log("🟡 帰還モード開始！")

    def emergency_stop(self):
        self.emergency = True
        self.mode_label.setText("現在のモード: ⛔ 緊急停止！")
        self.mode_label.setStyleSheet("font-size: 14px; color: #ff0000; font-weight: bold;")
        self.alert_label.setText("⛔ 緊急停止実行！")
        self.alert_label.setStyleSheet("font-size: 13px; color: #ff0000;")
        self.add_log("⛔ 緊急停止！全システム停止")

    def toggle_manual(self):
        self.manual_mode = not self.manual_mode
        if self.manual_mode:
            self.btn_manual.setText("🕹️ 手動モード")
            self.btn_manual.setStyleSheet("""
                QPushButton {
                    background-color: #440000;
                    color: #ff4444;
                    border: 2px solid #ff4444;
                    padding: 8px;
                    font-size: 12px;
                    border-radius: 4px;
                }
            """)
            self.add_log("🕹️ 手動モードに切替！TX16Sで直接操作可能")
            self.mode_label.setText("現在のモード: 🕹️ 手動操作中")
            self.mode_label.setStyleSheet("font-size: 14px; color: #ff4444; font-weight: bold;")
        else:
            self.btn_manual.setText("🤖 自動モード")
            self.btn_manual.setStyleSheet("""
                QPushButton {
                    background-color: #003300;
                    color: #00ff88;
                    border: 2px solid #00ff88;
                    padding: 8px;
                    font-size: 12px;
                    border-radius: 4px;
                }
            """)
            self.add_log("🤖 自動モードに復帰！PHENIXが制御")
            self.mode_label.setText("現在のモード: 🤖 自動モード")
            self.mode_label.setStyleSheet("font-size: 14px; color: #00ff88; font-weight: bold;")

    def toggle_auto_return(self):
        self.auto_return_enabled = not self.auto_return_enabled
        if self.auto_return_enabled:
            self.btn_auto_return.setText("🔒 自動帰還: ON")
            self.btn_auto_return.setStyleSheet("""
                QPushButton {
                    background-color: #003300;
                    color: #00ff88;
                    border: 2px solid #00ff88;
                    padding: 8px;
                    font-size: 12px;
                    border-radius: 4px;
                }
            """)
            self.add_log("🔒 自動帰還（15%）：ON")
        else:
            self.btn_auto_return.setText("🔓 自動帰還: OFF")
            self.btn_auto_return.setStyleSheet("""
                QPushButton {
                    background-color: #440000;
                    color: #ff4444;
                    border: 2px solid #ff4444;
                    padding: 8px;
                    font-size: 12px;
                    border-radius: 4px;
                }
            """)
            self.add_log("🔓 自動帰還（15%）：OFF（解除中）")

    def drop_node(self):
        if self.node_count > 0:
            self.node_count -= 1
            self.node_count_label.setText(f"ノード残数: {self.node_count}個")
            node_pos = [
                self.mother_pos[0] + random.uniform(-0.001, 0.001),
                self.mother_pos[1] + random.uniform(-0.001, 0.001)
            ]
            self.nodes.append(node_pos)
            self.add_log(f"🚀 ノード投下！残り{self.node_count}個")
            self.update_map()
            if len(self.nodes) <= 3:
                getattr(self, f'node_gps_{len(self.nodes)-1}').setText(
                    f"ノード{len(self.nodes)}: {node_pos[0]:.4f}, {node_pos[1]:.4f}"
                )
        else:
            self.add_log("❌ ノード残数が0です！")

    def toggle_thermal(self):
        self.thermal_running = not self.thermal_running
        if self.thermal_running:
            self.thermal_timer.start(200)
            self.add_log("🌡️ サーマル検知開始！")
        else:
            self.thermal_timer.stop()
            self.add_log("🌡️ サーマル検知停止")

    def update_thermal(self):
        frame = self.thermal.generate_frame()
        detected = self.thermal.detect_survivors(frame, 35.0)

        frame_norm = cv2.normalize(frame, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        frame_color = cv2.applyColorMap(frame_norm, cv2.COLORMAP_INFERNO)

        for det in detected:
            sx, sy = det['x'] * 2, det['y'] * 2
            cv2.circle(frame_color, (sx, sy), 20, (0, 255, 0), 2)
            cv2.putText(frame_color, f"{det['temp']:.1f}C",
                       (sx - 20, sy - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        frame_large = cv2.resize(frame_color, (640, 480))
        h, w, c = frame_large.shape
        qt_image = QImage(frame_large.data, w, h, c * w, QImage.Format.Format_RGB888)
        qt_image = qt_image.rgbSwapped()
        self.thermal_label.setPixmap(QPixmap.fromImage(qt_image))

        if detected:
            self.survivor_count.setText(f"検知数: {len(detected)}人")
            lat = self.drone_pos[0] + (detected[0]['y'] - 120) * 0.00001
            lng = self.drone_pos[1] + (detected[0]['x'] - 160) * 0.00001
            self.survivor_coords.setText(f"座標: {lat:.4f}, {lng:.4f}")

            if len(detected) != len(self.survivors_detected):
                self.survivors_detected = detected
                self.add_log(f"⚠️ 生存者{len(detected)}人検知！座標: {lat:.4f}, {lng:.4f}")
                self.alert_label.setText(f"⚠️ 生存者{len(detected)}人検知！")
                self.alert_label.setStyleSheet("font-size: 13px; color: #ff4444; font-weight: bold;")

                survivor_map_pos = [lat, lng]
                if survivor_map_pos not in self.nodes:
                    self.update_map(survivor_pos=(lat, lng))

    def simulate_obstacle(self):
        if self.current_mode == "追従モード" and not self.emergency and not self.manual_mode:
            if random.random() < 0.2:
                self.obstacle_detected = True
                self.obstacle_label.setText("⚠️ 障害物検知！回避中...")
                self.obstacle_label.setStyleSheet("font-size: 13px; color: #ff4444; font-weight: bold;")
                self.add_log("⚠️ 障害物検知！自動回避行動開始")
                QTimer.singleShot(3000, self.obstacle_cleared)

    def obstacle_cleared(self):
        self.obstacle_detected = False
        self.obstacle_label.setText("✅ 障害物クリア・追従復帰")
        self.obstacle_label.setStyleSheet("font-size: 13px; color: #00ff88;")
        self.add_log("✅ 障害物回避完了！追従モードに復帰")
        QTimer.singleShot(2000, lambda: self.obstacle_label.setText("✅ 障害物なし"))

    def update_map(self, survivor_pos=None):
        m = folium.Map(location=self.mother_pos, zoom_start=14, tiles='CartoDB positron')

        folium.Marker(self.mother_pos, tooltip="🔴 母艦",
                     icon=folium.Icon(color='red', icon='home', prefix='fa')).add_to(m)
        folium.Circle(self.mother_pos, radius=500, color='#00ff88',
                     fill=True, fill_opacity=0.1).add_to(m)

        folium.Marker(self.drone_pos, tooltip="🔵 ドローン",
                     icon=folium.Icon(color='blue', icon='plane', prefix='fa')).add_to(m)

        for i, node in enumerate(self.nodes):
            folium.Marker(node, tooltip=f"🟡 ノード{i+1}",
                         icon=folium.Icon(color='orange', icon='wifi', prefix='fa')).add_to(m)
            folium.Circle(node, radius=500, color='#ffaa00',
                         fill=True, fill_opacity=0.1).add_to(m)

        if survivor_pos:
            folium.Marker(survivor_pos, tooltip="⚠️ 生存者検知！",
                         popup=f"生存者\n{survivor_pos[0]:.4f}, {survivor_pos[1]:.4f}",
                         icon=folium.Icon(color='red', icon='user', prefix='fa')).add_to(m)

        m.save(self.map_file)

    def open_map(self):
        subprocess.Popen(['firefox', self.map_file])
        self.add_log("🌐 地図をFirefoxで開きました")

    def check_auto_return(self, drone_battery):
        if self.auto_return_enabled and drone_battery <= 15 and not self.auto_return_triggered:
            self.auto_return_triggered = True
            self.start_return()
            self.alert_label.setText("⚠️ バッテリー低下！自動帰還中")
            self.alert_label.setStyleSheet("font-size: 13px; color: #ff4444;")
            self.add_log(f"⚠️ バッテリー{drone_battery}%！自動帰還開始！")

    def update_display(self):
        if self.emergency:
            return

        rssi = random.randint(-95, -55)
        self.rssi_label.setText(f"RSSI: {rssi} dBm")
        self.rssi_graph.update_graph(rssi)

        if rssi < -85:
            self.rssi_label.setStyleSheet("font-size: 16px; color: #ff4444;")
            self.countdown_value += 1
            remaining = max(0, 7 - self.countdown_value)
            self.countdown_label.setText(f"⚠️ 投下まで: {remaining}秒...")
            if self.countdown_value >= 7 and self.node_count > 0:
                self.drop_node()
                self.countdown_value = 0
        else:
            self.rssi_label.setStyleSheet("font-size: 16px; color: #00ff88;")
            self.countdown_label.setText("投下まで: 待機中")
            self.countdown_value = 0

        drone_bat = random.randint(60, 100)
        mother_bat = random.randint(70, 100)
        self.battery_drone.setValue(drone_bat)
        self.battery_mother.setValue(mother_bat)
        self.bat_drone_label.setText(f"ドローン: {drone_bat}%")
        self.bat_mother_label.setText(f"母艦: {mother_bat}%")
        self.check_auto_return(drone_bat)

        self.mother_pos[1] += random.uniform(0, 0.0001)
        self.drone_pos = [self.mother_pos[0] + random.uniform(-0.0005, 0.0005),
                         self.mother_pos[1] + random.uniform(-0.0005, 0.0005)]

        self.mother_gps.setText(f"母艦: {self.mother_pos[0]:.4f}, {self.mother_pos[1]:.4f}")
        self.drone_gps.setText(f"ドローン: {self.drone_pos[0]:.4f}, {self.drone_pos[1]:.4f}")

        temp = random.uniform(20, 35)
        humid = random.uniform(40, 80)
        pressure = random.uniform(1010, 1020)
        alt = random.uniform(10, 50)
        spd = random.uniform(0, 30)
        hdg = random.uniform(0, 360)

        self.temperature.setText(f"気温: {temp:.1f} ℃")
        self.humidity.setText(f"湿度: {humid:.1f} %")
        self.pressure_label.setText(f"気圧: {pressure:.1f} hPa")
        self.drone_alt.setText(f"高度: {alt:.1f} m")
        self.drone_speed.setText(f"速度: {spd:.1f} km/h")
        self.drone_heading.setText(f"方位: {hdg:.0f} °")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PHENIXIntegrated()
    window.show()
    sys.exit(app.exec())