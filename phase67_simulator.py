import sys
import os
import math
import random
import subprocess
import folium
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np


class VTOLState:
    """VTOLの状態管理"""
    DOCKED = "ドック待機"
    LAUNCHING = "離陸中"
    FLYING = "飛行中"
    RETURNING = "帰還中"
    CHARGING = "充電中"


class VTOL:
    def __init__(self, vtol_id, name):
        self.id = vtol_id
        self.name = name
        self.state = VTOLState.DOCKED
        self.battery = 100
        self.lat = -33.2833
        self.lng = 149.1000
        self.altitude = 0
        self.flight_time = 0
        self.total_flights = 0
        self.charging_time = 0

    def update(self):
        if self.state == VTOLState.FLYING:
            self.battery -= random.uniform(0.3, 0.8)
            self.flight_time += 1
            self.lat += random.uniform(-0.0002, 0.0002)
            self.lng += random.uniform(-0.0002, 0.0002)
            self.altitude = random.uniform(25, 50)
            if self.battery <= 15:
                self.state = VTOLState.RETURNING
        elif self.state == VTOLState.RETURNING:
            self.altitude = max(0, self.altitude - 2)
            self.battery -= 0.2
            if self.altitude <= 0:
                self.state = VTOLState.CHARGING
                self.total_flights += 1
        elif self.state == VTOLState.CHARGING:
            self.battery = min(100, self.battery + 2)
            self.charging_time += 1
            self.altitude = 0
            if self.battery >= 95:
                self.state = VTOLState.DOCKED
                self.charging_time = 0
        elif self.state == VTOLState.LAUNCHING:
            self.altitude = min(30, self.altitude + 3)
            self.battery -= 0.2
            if self.altitude >= 30:
                self.state = VTOLState.FLYING

    def launch(self):
        if self.state == VTOLState.DOCKED and self.battery > 20:
            self.state = VTOLState.LAUNCHING
            return True
        return False

    def force_return(self):
        if self.state in [VTOLState.FLYING, VTOLState.LAUNCHING]:
            self.state = VTOLState.RETURNING


class Node:
    def __init__(self, node_id, lat, lng):
        self.id = node_id
        self.lat = lat
        self.lng = lng
        self.rssi = random.randint(-80, -60)
        self.battery = 100
        self.active = True
        self.radar_detections = 0

    def update(self):
        self.rssi = random.randint(-90, -55)
        self.battery = max(0, self.battery - random.uniform(0, 0.1))
        self.radar_detections = random.randint(0, 5)


class SimulationGraph(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(6, 4), facecolor='#1a1a2e')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#0a0a1a')
        super().__init__(self.fig)
        self.battery_history = {1: [], 2: []}

    def update_graph(self, vtol1, vtol2):
        self.battery_history[1].append(vtol1.battery)
        self.battery_history[2].append(vtol2.battery)
        if len(self.battery_history[1]) > 60:
            self.battery_history[1].pop(0)
            self.battery_history[2].pop(0)

        self.ax.clear()
        self.ax.set_facecolor('#0a0a1a')
        self.ax.set_ylim(0, 105)
        self.ax.set_title('VTOL バッテリー推移', color='#00ff88', fontsize=10)
        self.ax.tick_params(colors='#00ff88')
        for spine in self.ax.spines.values():
            spine.set_color('#00ff88')
        self.ax.axhline(y=15, color='#ff4444', linestyle='--', label='自動帰還ライン')
        self.ax.plot(self.battery_history[1], color='#00aaff', label='Y3①', linewidth=2)
        self.ax.plot(self.battery_history[2], color='#ffaa00', label='Y3②', linewidth=2)
        self.ax.legend(facecolor='#1a1a2e', labelcolor='#00ff88', fontsize=8)
        self.draw()


class Phase67Simulator(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔥 PHENIX Phase 6・7 シミュレーター")
        self.setGeometry(50, 50, 1400, 900)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        self.base_lat = -33.2833
        self.base_lng = 149.1000
        self.map_file = os.path.expanduser("~/PHENIX/phase67_map.html")
        self.running = False
        self.step = 0

        self.vtol1 = VTOL(1, "Y3①")
        self.vtol2 = VTOL(2, "Y3②")
        self.vtol2.battery = 50

        self.nodes = [
            Node(i+1,
                 self.base_lat + random.uniform(-0.005, 0.005),
                 self.base_lng + random.uniform(-0.005, 0.005))
            for i in range(8)
        ]

        self.starlink_active = False
        self.satcom_active = False
        self.comm_mode = "LoRa"

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("🔥 PHENIX Phase 6・7 完成形シミュレーター")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        subtitle = QLabel("VTOL2機交互運用 | 分散レーダー | Starlink | SatCom | 5段階冗長通信")
        subtitle.setStyleSheet("font-size: 12px; color: #666666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle)

        content_layout = QHBoxLayout()

        # 左パネル
        left_panel = QWidget()
        left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_panel)

        # コントロール
        ctrl_group = QGroupBox("🎮 システムコントロール")
        ctrl_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 2px solid #00ff88; padding: 5px; }"
        )
        ctrl_layout = QVBoxLayout()

        self.btn_start = QPushButton("▶️ シミュレーション開始")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                color: #00ff88;
                border: 2px solid #00ff88;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #005500; }
        """)
        self.btn_start.clicked.connect(self.toggle_simulation)
        ctrl_layout.addWidget(self.btn_start)

        btn_layout = QHBoxLayout()

        btn_launch1 = QPushButton("🚁 Y3① 出撃")
        btn_launch1.setStyleSheet("""
            QPushButton {
                background-color: #000044;
                color: #00aaff;
                border: 2px solid #00aaff;
                padding: 8px;
                font-size: 12px;
                border-radius: 5px;
            }
        """)
        btn_launch1.clicked.connect(lambda: self.manual_launch(self.vtol1))
        btn_layout.addWidget(btn_launch1)

        btn_launch2 = QPushButton("🚁 Y3② 出撃")
        btn_launch2.setStyleSheet("""
            QPushButton {
                background-color: #444400;
                color: #ffaa00;
                border: 2px solid #ffaa00;
                padding: 8px;
                font-size: 12px;
                border-radius: 5px;
            }
        """)
        btn_launch2.clicked.connect(lambda: self.manual_launch(self.vtol2))
        btn_layout.addWidget(btn_launch2)

        ctrl_layout.addLayout(btn_layout)

        btn_layout2 = QHBoxLayout()

        btn_return1 = QPushButton("🏠 Y3① 帰還")
        btn_return1.setStyleSheet("""
            QPushButton {
                background-color: #222222;
                color: #aaaaaa;
                border: 1px solid #aaaaaa;
                padding: 8px;
                font-size: 12px;
                border-radius: 5px;
            }
        """)
        btn_return1.clicked.connect(lambda: self.vtol1.force_return())
        btn_layout2.addWidget(btn_return1)

        btn_return2 = QPushButton("🏠 Y3② 帰還")
        btn_return2.setStyleSheet("""
            QPushButton {
                background-color: #222222;
                color: #aaaaaa;
                border: 1px solid #aaaaaa;
                padding: 8px;
                font-size: 12px;
                border-radius: 5px;
            }
        """)
        btn_return2.clicked.connect(lambda: self.vtol2.force_return())
        btn_layout2.addWidget(btn_return2)

        ctrl_layout.addLayout(btn_layout2)

        # 通信切替
        comm_layout = QHBoxLayout()
        self.btn_starlink = QPushButton("🛰️ Starlink OFF")
        self.btn_starlink.setStyleSheet("""
            QPushButton {
                background-color: #222222;
                color: #666666;
                border: 1px solid #666666;
                padding: 8px;
                font-size: 11px;
                border-radius: 5px;
            }
        """)
        self.btn_starlink.clicked.connect(self.toggle_starlink)
        comm_layout.addWidget(self.btn_starlink)

        self.btn_satcom = QPushButton("📡 SatCom OFF")
        self.btn_satcom.setStyleSheet("""
            QPushButton {
                background-color: #222222;
                color: #666666;
                border: 1px solid #666666;
                padding: 8px;
                font-size: 11px;
                border-radius: 5px;
            }
        """)
        self.btn_satcom.clicked.connect(self.toggle_satcom)
        comm_layout.addWidget(self.btn_satcom)

        ctrl_layout.addLayout(comm_layout)

        btn_map = QPushButton("🗺️ 地図を開く")
        btn_map.setStyleSheet("""
            QPushButton {
                background-color: #003333;
                color: #00ffff;
                border: 2px solid #00ffff;
                padding: 8px;
                font-size: 12px;
                border-radius: 5px;
            }
        """)
        btn_map.clicked.connect(self.open_map)
        ctrl_layout.addWidget(btn_map)

        ctrl_group.setLayout(ctrl_layout)
        left_layout.addWidget(ctrl_group)

        # VTOL状態
        vtol_group = QGroupBox("🚁 VTOL状態")
        vtol_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        vtol_layout = QVBoxLayout()

        # Y3①
        vtol1_label = QLabel("── ArgusFPV Y3① ──")
        vtol1_label.setStyleSheet("color: #00aaff; font-size: 12px; font-weight: bold;")
        vtol_layout.addWidget(vtol1_label)

        self.vtol1_state = QLabel("状態: ドック待機")
        self.vtol1_state.setStyleSheet("font-size: 12px; color: #00aaff;")
        vtol_layout.addWidget(self.vtol1_state)

        self.vtol1_battery = QProgressBar()
        self.vtol1_battery.setStyleSheet("QProgressBar::chunk { background-color: #00aaff; }")
        self.vtol1_battery.setValue(100)
        vtol_layout.addWidget(self.vtol1_battery)

        self.vtol1_info = QLabel("高度: 0m | 飛行回数: 0")
        self.vtol1_info.setStyleSheet("font-size: 11px; color: #666666;")
        vtol_layout.addWidget(self.vtol1_info)

        # Y3②
        vtol2_label = QLabel("── ArgusFPV Y3② ──")
        vtol2_label.setStyleSheet("color: #ffaa00; font-size: 12px; font-weight: bold;")
        vtol_layout.addWidget(vtol2_label)

        self.vtol2_state = QLabel("状態: ドック待機")
        self.vtol2_state.setStyleSheet("font-size: 12px; color: #ffaa00;")
        vtol_layout.addWidget(self.vtol2_state)

        self.vtol2_battery = QProgressBar()
        self.vtol2_battery.setStyleSheet("QProgressBar::chunk { background-color: #ffaa00; }")
        self.vtol2_battery.setValue(50)
        vtol_layout.addWidget(self.vtol2_battery)

        self.vtol2_info = QLabel("高度: 0m | 飛行回数: 0")
        self.vtol2_info.setStyleSheet("font-size: 11px; color: #666666;")
        vtol_layout.addWidget(self.vtol2_info)

        vtol_group.setLayout(vtol_layout)
        left_layout.addWidget(vtol_group)

        # 通信状態
        comm_group = QGroupBox("📡 5段階冗長通信")
        comm_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        comm_layout2 = QVBoxLayout()

        self.comm_labels = []
        comms = [
            ("WiFi/4G/5G", "#00ff88"),
            ("LoRaメッシュ", "#00aaff"),
            ("デュアル通信", "#ffaa00"),
            ("Starlink", "#ff66ff"),
            ("SatCom", "#ff4444"),
        ]
        for name, color in comms:
            label = QLabel(f"● {name}: 待機中")
            label.setStyleSheet(f"font-size: 11px; color: #444444;")
            comm_layout2.addWidget(label)
            self.comm_labels.append((label, color))

        self.comm_mode_label = QLabel("現在: LoRaメッシュ")
        self.comm_mode_label.setStyleSheet(
            "font-size: 13px; color: #00aaff; font-weight: bold;"
        )
        comm_layout2.addWidget(self.comm_mode_label)

        comm_group.setLayout(comm_layout2)
        left_layout.addWidget(comm_group)

        # ノード状態
        node_group = QGroupBox("📡 ノードネットワーク（8個）")
        node_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        node_layout = QVBoxLayout()
        self.node_labels = []
        for i in range(8):
            label = QLabel(f"ノード{i+1}: 待機中")
            label.setStyleSheet("font-size: 10px; color: #444444;")
            node_layout.addWidget(label)
            self.node_labels.append(label)
        node_group.setLayout(node_layout)
        left_layout.addWidget(node_group)

        content_layout.addWidget(left_panel)

        # 右パネル
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # システム状態表示
        status_layout = QHBoxLayout()

        self.sky_status = QLabel("🌤️ 上空監視: 待機中")
        self.sky_status.setStyleSheet(
            "font-size: 14px; color: #666666; font-weight: bold;"
        )
        status_layout.addWidget(self.sky_status)

        self.network_status = QLabel("🌐 ネットワーク: 待機中")
        self.network_status.setStyleSheet(
            "font-size: 14px; color: #666666; font-weight: bold;"
        )
        status_layout.addWidget(self.network_status)

        self.coverage_label = QLabel("📡 カバレッジ: 0 km²")
        self.coverage_label.setStyleSheet("font-size: 14px; color: #ff66ff;")
        status_layout.addWidget(self.coverage_label)

        right_layout.addLayout(status_layout)

        self.graph = SimulationGraph()
        right_layout.addWidget(self.graph)

        # アラート
        self.alert_label = QLabel("✅ 全システム待機中")
        self.alert_label.setStyleSheet(
            "font-size: 16px; color: #00ff88; font-weight: bold;"
        )
        self.alert_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.alert_label)

        self.log_text = QTextEdit()
        self.log_text.setStyleSheet(
            "background-color: #050510; color: #00ff88; font-family: monospace; font-size: 11px;"
        )
        self.log_text.setReadOnly(True)
        right_layout.addWidget(self.log_text)

        content_layout.addWidget(right_panel)
        main_layout.addLayout(content_layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)

        self.update_map()
        self.log("🔥 PHENIX Phase 6・7 シミュレーター起動！")
        self.log("✅ ArgusFPV Y3 × 2機 準備完了")
        self.log("✅ LoRaノード 8個 配置完了")
        self.log("✅ 5段階冗長通信システム準備完了")
        self.log("「シミュレーション開始」ボタンで開始！")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def toggle_simulation(self):
        self.running = not self.running
        if self.running:
            self.timer.start(500)
            self.btn_start.setText("⏹️ 停止")
            self.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #440000;
                    color: #ff4444;
                    border: 2px solid #ff4444;
                    padding: 10px;
                    font-size: 14px;
                    border-radius: 5px;
                }
            """)
            self.log("▶️ Phase 6・7 シミュレーション開始！")
            self.vtol1.launch()
            self.log("🚁 Y3① 自動出撃！")
        else:
            self.timer.stop()
            self.btn_start.setText("▶️ シミュレーション開始")
            self.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #003300;
                    color: #00ff88;
                    border: 2px solid #00ff88;
                    padding: 10px;
                    font-size: 14px;
                    border-radius: 5px;
                }
            """)
            self.log("⏹️ シミュレーション停止")

    def manual_launch(self, vtol):
        if vtol.launch():
            self.log(f"🚁 {vtol.name} 手動出撃！バッテリー: {vtol.battery:.0f}%")
        else:
            self.log(f"⚠️ {vtol.name} 出撃不可（状態: {vtol.state}）")

    def toggle_starlink(self):
        self.starlink_active = not self.starlink_active
        if self.starlink_active:
            self.btn_starlink.setText("🛰️ Starlink ON")
            self.btn_starlink.setStyleSheet("""
                QPushButton {
                    background-color: #440044;
                    color: #ff66ff;
                    border: 2px solid #ff66ff;
                    padding: 8px;
                    font-size: 11px;
                    border-radius: 5px;
                }
            """)
            self.log("🛰️ Starlink接続！グローバル通信有効化")
        else:
            self.btn_starlink.setText("🛰️ Starlink OFF")
            self.btn_starlink.setStyleSheet("""
                QPushButton {
                    background-color: #222222;
                    color: #666666;
                    border: 1px solid #666666;
                    padding: 8px;
                    font-size: 11px;
                    border-radius: 5px;
                }
            """)
            self.log("🛰️ Starlink切断")

    def toggle_satcom(self):
        self.satcom_active = not self.satcom_active
        if self.satcom_active:
            self.btn_satcom.setText("📡 SatCom ON")
            self.btn_satcom.setStyleSheet("""
                QPushButton {
                    background-color: #440000;
                    color: #ff4444;
                    border: 2px solid #ff4444;
                    padding: 8px;
                    font-size: 11px;
                    border-radius: 5px;
                }
            """)
            self.log("📡 SatCom（RockBLOCK）接続！衛星通信有効化")
        else:
            self.btn_satcom.setText("📡 SatCom OFF")
            self.btn_satcom.setStyleSheet("""
                QPushButton {
                    background-color: #222222;
                    color: #666666;
                    border: 1px solid #666666;
                    padding: 8px;
                    font-size: 11px;
                    border-radius: 5px;
                }
            """)
            self.log("📡 SatCom切断")

    def update_comm_status(self):
        modes = ["WiFi/4G/5G", "LoRaメッシュ", "デュアル通信", "Starlink", "SatCom"]
        active_count = 2
        if self.starlink_active:
            active_count = 4
        if self.satcom_active:
            active_count = 5

        for i, (label, color) in enumerate(self.comm_labels):
            if i < active_count:
                label.setText(f"✅ {modes[i]}: 稼働中")
                label.setStyleSheet(f"font-size: 11px; color: {color};")
            else:
                label.setText(f"● {modes[i]}: 待機中")
                label.setStyleSheet("font-size: 11px; color: #444444;")

        if self.satcom_active:
            self.comm_mode_label.setText("現在: 5段階冗長通信 完全稼働！")
            self.comm_mode_label.setStyleSheet(
                "font-size: 13px; color: #ff4444; font-weight: bold;"
            )
        elif self.starlink_active:
            self.comm_mode_label.setText("現在: Starlink + LoRa")
            self.comm_mode_label.setStyleSheet(
                "font-size: 13px; color: #ff66ff; font-weight: bold;"
            )
        else:
            self.comm_mode_label.setText("現在: LoRaメッシュ")
            self.comm_mode_label.setStyleSheet(
                "font-size: 13px; color: #00aaff; font-weight: bold;"
            )

    def update_simulation(self):
        self.step += 1

        # VTOL更新
        self.vtol1.update()
        self.vtol2.update()

        # 交互運用ロジック
        v1_flying = self.vtol1.state == VTOLState.FLYING
        v2_flying = self.vtol2.state == VTOLState.FLYING

        if not v1_flying and not v2_flying:
            if self.vtol1.state == VTOLState.DOCKED and self.vtol1.battery > 20:
                self.vtol1.launch()
                self.log(f"🚁 Y3① 自動出撃！バッテリー: {self.vtol1.battery:.0f}%")
            elif self.vtol2.state == VTOLState.DOCKED and self.vtol2.battery > 20:
                self.vtol2.launch()
                self.log(f"🚁 Y3② 自動出撃！バッテリー: {self.vtol2.battery:.0f}%")

        # VTOL UI更新
        self.vtol1_state.setText(f"状態: {self.vtol1.state}")
        self.vtol1_battery.setValue(int(self.vtol1.battery))
        self.vtol1_info.setText(
            f"高度: {self.vtol1.altitude:.0f}m | 飛行回数: {self.vtol1.total_flights}"
        )

        self.vtol2_state.setText(f"状態: {self.vtol2.state}")
        self.vtol2_battery.setValue(int(self.vtol2.battery))
        self.vtol2_info.setText(
            f"高度: {self.vtol2.altitude:.0f}m | 飛行回数: {self.vtol2.total_flights}"
        )

        # 上空監視状態
        if v1_flying or v2_flying:
            self.sky_status.setText("🌤️ 上空監視: 🟢 稼働中")
            self.sky_status.setStyleSheet(
                "font-size: 14px; color: #00ff88; font-weight: bold;"
            )
        else:
            self.sky_status.setText("🌤️ 上空監視: 🔴 切替中...")
            self.sky_status.setStyleSheet(
                "font-size: 14px; color: #ff4444; font-weight: bold;"
            )

        # ノード更新
        total_detections = 0
        for i, node in enumerate(self.nodes):
            node.update()
            if node.active:
                self.node_labels[i].setText(
                    f"ノード{i+1}: RSSI {node.rssi}dBm | 検知{node.radar_detections}"
                )
                self.node_labels[i].setStyleSheet("font-size: 10px; color: #00ff88;")
                total_detections += node.radar_detections
            else:
                self.node_labels[i].setText(f"ノード{i+1}: ❌ オフライン")
                self.node_labels[i].setStyleSheet("font-size: 10px; color: #ff4444;")

        # ネットワーク状態
        active_nodes = sum(1 for n in self.nodes if n.active)
        self.network_status.setText(f"🌐 ネットワーク: {active_nodes}/8ノード稼働")
        self.network_status.setStyleSheet(
            "font-size: 14px; color: #00ff88; font-weight: bold;"
        )

        # カバレッジ計算
        import math
        area = math.pi * 0.006**2 * active_nodes
        self.coverage_label.setText(f"📡 カバレッジ: {area:.2f} km²")

        # アラート
        if total_detections > 10:
            self.alert_label.setText(f"⚠️ 広域で{total_detections}件の検知！")
            self.alert_label.setStyleSheet(
                "font-size: 16px; color: #ff4444; font-weight: bold;"
            )
        elif v1_flying or v2_flying:
            self.alert_label.setText("✅ 上空監視・分散センシング稼働中")
            self.alert_label.setStyleSheet(
                "font-size: 16px; color: #00ff88; font-weight: bold;"
            )

        self.update_comm_status()
        self.graph.update_graph(self.vtol1, self.vtol2)

        if self.step % 10 == 0:
            self.update_map()

    def update_map(self):
        m = folium.Map(
            location=[self.base_lat, self.base_lng],
            zoom_start=14,
            tiles='CartoDB positron'
        )

        # 母艦
        folium.Marker(
            [self.base_lat, self.base_lng],
            tooltip="🔴 母艦",
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(m)

        # VTOL1
        if self.vtol1.state == VTOLState.FLYING:
            folium.Marker(
                [self.vtol1.lat, self.vtol1.lng],
                tooltip=f"🔵 Y3① ({self.vtol1.battery:.0f}%)",
                icon=folium.Icon(color='blue', icon='plane', prefix='fa')
            ).add_to(m)

        # VTOL2
        if self.vtol2.state == VTOLState.FLYING:
            folium.Marker(
                [self.vtol2.lat, self.vtol2.lng],
                tooltip=f"🟡 Y3② ({self.vtol2.battery:.0f}%)",
                icon=folium.Icon(color='orange', icon='plane', prefix='fa')
            ).add_to(m)

        # ノード
        for node in self.nodes:
            folium.Marker(
                [node.lat, node.lng],
                tooltip=f"📡 ノード{node.id} RSSI:{node.rssi}dBm",
                icon=folium.Icon(color='green', icon='wifi', prefix='fa')
            ).add_to(m)
            folium.Circle(
                [node.lat, node.lng],
                radius=300,
                color='#00ff88',
                fill=True,
                fill_opacity=0.05
            ).add_to(m)

        # Starlink
        if self.starlink_active:
            folium.Marker(
                [self.base_lat + 0.01, self.base_lng],
                tooltip="🛰️ Starlink接続中",
                icon=folium.Icon(color='purple', icon='signal', prefix='fa')
            ).add_to(m)

        m.save(self.map_file)

    def open_map(self):
        subprocess.Popen(['firefox', self.map_file])
        self.log("🌐 地図をFirefoxで開きました")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Phase67Simulator()
    window.show()
    sys.exit(app.exec())