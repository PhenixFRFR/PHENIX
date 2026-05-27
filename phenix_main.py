import sys
import random
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from lora_manager import LoRaManager
from mavlink_bridge import MAVLinkBridge


class RSSIGraph(FigureCanvas):

    def __init__(self):
        self.fig = Figure(figsize=(5, 2), facecolor='#1a1a2e')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#0a0a1a')
        self.ax.tick_params(colors='#00ff88')
        for spine in self.ax.spines.values():
            spine.set_color('#00ff88')
        self.ax.set_ylim(-120, -40)
        self.ax.set_title('RSSI履歴', color='#00ff88')
        super().__init__(self.fig)
        self.rssi_data = []

    def update_graph(self, rssi):
        self.rssi_data.append(rssi)
        if len(self.rssi_data) > 60:
            self.rssi_data.pop(0)
        self.ax.clear()
        self.ax.set_facecolor('#0a0a1a')
        self.ax.set_ylim(-120, -40)
        self.ax.set_title('RSSI履歴 (直近60秒)', color='#00ff88')
        self.ax.tick_params(colors='#00ff88')
        for spine in self.ax.spines.values():
            spine.set_color('#00ff88')
        self.ax.axhline(y=-85, color='#ff4444', linestyle='--', label='-85dBm')
        colors = ['#ff4444' if r < -85 else '#00ff88' for r in self.rssi_data]
        self.ax.bar(range(len(self.rssi_data)), self.rssi_data, color=colors, alpha=0.7)
        self.ax.legend(facecolor='#1a1a2e', labelcolor='#00ff88')
        self.draw()


class PHENIXMain(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PHENIX Command Center v3.1 - 統合システム")
        self.setGeometry(100, 100, 1400, 1000)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        self.lora = LoRaManager()
        self.mavlink = MAVLinkBridge()
        self.mavlink.connect()

        self.node_count = 3
        self.countdown_value = 0
        self.current_mode = "待機中"
        self.auto_drop = True
        self.emergency = False

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QGridLayout(main_widget)

        # タイトル
        title = QLabel("🔥 PHENIX Command Center v3.1")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title, 0, 0, 1, 4)

        # 接続状態
        self.connection_status = QLabel("🔗 MAVLink: 接続中 | LoRa: 待機中 | DB: 稼働中")
        self.connection_status.setStyleSheet("font-size: 12px; color: #00aaff;")
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.connection_status, 1, 0, 1, 4)

        # 操作ボタンパネル
        control_group = QGroupBox("🎮 操作パネル")
        control_group.setStyleSheet("QGroupBox { color: #00ff88; border: 2px solid #00ff88; padding: 5px; }")
        control_layout = QHBoxLayout()

        # 追従モードボタン
        self.btn_follow = QPushButton("🟢 追従モード開始")
        self.btn_follow.setStyleSheet("""
            QPushButton {
                background-color: #004400;
                color: #00ff88;
                border: 2px solid #00ff88;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #006600; }
            QPushButton:pressed { background-color: #00ff88; color: #000000; }
        """)
        self.btn_follow.clicked.connect(self.start_follow_mode)
        control_layout.addWidget(self.btn_follow)

        # 追従解除ボタン
        self.btn_hover = QPushButton("🔴 追従解除")
        self.btn_hover.setStyleSheet("""
            QPushButton {
                background-color: #440000;
                color: #ff4444;
                border: 2px solid #ff4444;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #660000; }
            QPushButton:pressed { background-color: #ff4444; color: #000000; }
        """)
        self.btn_hover.clicked.connect(self.stop_follow_mode)
        control_layout.addWidget(self.btn_hover)

        # 旋回モードボタン
        self.btn_circle = QPushButton("🔵 旋回モード")
        self.btn_circle.setStyleSheet("""
            QPushButton {
                background-color: #000044;
                color: #00aaff;
                border: 2px solid #00aaff;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #000066; }
            QPushButton:pressed { background-color: #00aaff; color: #000000; }
        """)
        self.btn_circle.clicked.connect(self.start_circle_mode)
        control_layout.addWidget(self.btn_circle)

        # 帰還モードボタン
        self.btn_return = QPushButton("🟡 帰還モード")
        self.btn_return.setStyleSheet("""
            QPushButton {
                background-color: #444400;
                color: #ffaa00;
                border: 2px solid #ffaa00;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #666600; }
            QPushButton:pressed { background-color: #ffaa00; color: #000000; }
        """)
        self.btn_return.clicked.connect(self.start_return_mode)
        control_layout.addWidget(self.btn_return)

        # 緊急停止ボタン
        self.btn_emergency = QPushButton("⛔ 緊急停止")
        self.btn_emergency.setStyleSheet("""
            QPushButton {
                background-color: #ff0000;
                color: #ffffff;
                border: 3px solid #ffffff;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #cc0000; }
            QPushButton:pressed { background-color: #ffffff; color: #ff0000; }
        """)
        self.btn_emergency.clicked.connect(self.emergency_stop)
        control_layout.addWidget(self.btn_emergency)

        # ノード手動投下ボタン
        self.btn_drop = QPushButton("🚀 ノード手動投下")
        self.btn_drop.setStyleSheet("""
            QPushButton {
                background-color: #440044;
                color: #ff66ff;
                border: 2px solid #ff66ff;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #660066; }
            QPushButton:pressed { background-color: #ff66ff; color: #000000; }
        """)
        self.btn_drop.clicked.connect(self.manual_drop)
        control_layout.addWidget(self.btn_drop)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group, 2, 0, 1, 4)

        # 現在のモード表示
        self.mode_label = QLabel("現在のモード: 待機中")
        self.mode_label.setStyleSheet("font-size: 16px; color: #ffaa00; font-weight: bold;")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.mode_label, 3, 0, 1, 4)

        # RSSI パネル
        rssi_group = QGroupBox("📡 LoRa通信")
        rssi_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        rssi_layout = QVBoxLayout()
        self.rssi_label = QLabel("RSSI: --- dBm")
        self.rssi_label.setStyleSheet("font-size: 18px; color: #00ff88;")
        self.snr_label = QLabel("SNR: --- dB")
        self.snr_label.setStyleSheet("font-size: 14px; color: #00aaff;")
        self.countdown_label = QLabel("投下まで: 待機中")
        self.countdown_label.setStyleSheet("font-size: 14px; color: #ffaa00;")
        self.comm_mode = QLabel("通信モード: LoRa")
        self.comm_mode.setStyleSheet("font-size: 14px; color: #00aaff;")
        self.node_count_label = QLabel("ノード残数: 3個")
        self.node_count_label.setStyleSheet("font-size: 14px; color: #ffaa00;")
        rssi_layout.addWidget(self.rssi_label)
        rssi_layout.addWidget(self.snr_label)
        rssi_layout.addWidget(self.countdown_label)
        rssi_layout.addWidget(self.comm_mode)
        rssi_layout.addWidget(self.node_count_label)
        rssi_group.setLayout(rssi_layout)
        layout.addWidget(rssi_group, 4, 0)

        # バッテリーパネル
        battery_group = QGroupBox("🔋 バッテリー")
        battery_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        battery_layout = QVBoxLayout()
        self.battery_mother = QProgressBar()
        self.battery_mother.setStyleSheet("QProgressBar::chunk { background-color: #00ff88; }")
        self.battery_drone = QProgressBar()
        self.battery_drone.setStyleSheet("QProgressBar::chunk { background-color: #00aaff; }")
        self.battery_node = QProgressBar()
        self.battery_node.setStyleSheet("QProgressBar::chunk { background-color: #ffaa00; }")
        self.bat_mother_label = QLabel("母艦: 100%")
        self.bat_mother_label.setStyleSheet("color: #00ff88;")
        self.bat_drone_label = QLabel("ドローン: 100%")
        self.bat_drone_label.setStyleSheet("color: #00aaff;")
        self.bat_node_label = QLabel("ノード: 100%")
        self.bat_node_label.setStyleSheet("color: #ffaa00;")
        battery_layout.addWidget(self.bat_mother_label)
        battery_layout.addWidget(self.battery_mother)
        battery_layout.addWidget(self.bat_drone_label)
        battery_layout.addWidget(self.battery_drone)
        battery_layout.addWidget(self.bat_node_label)
        battery_layout.addWidget(self.battery_node)
        battery_group.setLayout(battery_layout)
        layout.addWidget(battery_group, 4, 1)

        # ドローン状態
        drone_group = QGroupBox("🚁 ドローン状態（MAVLink）")
        drone_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        drone_layout = QVBoxLayout()
        self.drone_mode = QLabel("モード: ---")
        self.drone_mode.setStyleSheet("font-size: 14px; color: #00ff88;")
        self.drone_armed = QLabel("アーム: ---")
        self.drone_armed.setStyleSheet("font-size: 14px; color: #ff4444;")
        self.drone_alt = QLabel("高度: --- m")
        self.drone_alt.setStyleSheet("font-size: 14px; color: #00aaff;")
        self.drone_speed = QLabel("速度: --- km/h")
        self.drone_speed.setStyleSheet("font-size: 14px; color: #00aaff;")
        self.drone_heading = QLabel("方位: --- °")
        self.drone_heading.setStyleSheet("font-size: 14px; color: #aa66ff;")
        self.drone_sats = QLabel("衛星: --- 機")
        self.drone_sats.setStyleSheet("font-size: 14px; color: #66ff66;")
        drone_layout.addWidget(self.drone_mode)
        drone_layout.addWidget(self.drone_armed)
        drone_layout.addWidget(self.drone_alt)
        drone_layout.addWidget(self.drone_speed)
        drone_layout.addWidget(self.drone_heading)
        drone_layout.addWidget(self.drone_sats)
        drone_group.setLayout(drone_layout)
        layout.addWidget(drone_group, 4, 2)

        # センサーパネル
        sensor_group = QGroupBox("🌡️ センサー")
        sensor_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        sensor_layout = QVBoxLayout()
        self.temperature = QLabel("気温: --- ℃")
        self.temperature.setStyleSheet("font-size: 14px; color: #ff6666;")
        self.humidity = QLabel("湿度: --- %")
        self.humidity.setStyleSheet("font-size: 14px; color: #66aaff;")
        self.pressure_label = QLabel("気圧: --- hPa")
        self.pressure_label.setStyleSheet("font-size: 14px; color: #66ff66;")
        self.radar_status = QLabel("レーダー: 待機中")
        self.radar_status.setStyleSheet("font-size: 14px; color: #ffaa00;")
        self.uwb_status = QLabel("UWB: 待機中")
        self.uwb_status.setStyleSheet("font-size: 14px; color: #aa66ff;")
        self.thermal_status = QLabel("サーマル: 待機中")
        self.thermal_status.setStyleSheet("font-size: 14px; color: #ff6666;")
        sensor_layout.addWidget(self.temperature)
        sensor_layout.addWidget(self.humidity)
        sensor_layout.addWidget(self.pressure_label)
        sensor_layout.addWidget(self.radar_status)
        sensor_layout.addWidget(self.uwb_status)
        sensor_layout.addWidget(self.thermal_status)
        sensor_group.setLayout(sensor_layout)
        layout.addWidget(sensor_group, 4, 3)

        # RSSIグラフ
        self.rssi_graph = RSSIGraph()
        layout.addWidget(self.rssi_graph, 5, 0, 1, 2)

        # GPS パネル
        gps_group = QGroupBox("📍 GPS位置情報")
        gps_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        gps_layout = QVBoxLayout()
        self.mother_gps = QLabel("母艦: ---, ---")
        self.mother_gps.setStyleSheet("font-size: 13px; color: #00ff88;")
        self.drone_gps = QLabel("ドローン: ---, ---")
        self.drone_gps.setStyleSheet("font-size: 13px; color: #00aaff;")
        self.node1_gps = QLabel("ノード1: ---, ---")
        self.node1_gps.setStyleSheet("font-size: 13px; color: #ffaa00;")
        self.node2_gps = QLabel("ノード2: ---, ---")
        self.node2_gps.setStyleSheet("font-size: 13px; color: #ffaa00;")
        self.node3_gps = QLabel("ノード3: ---, ---")
        self.node3_gps.setStyleSheet("font-size: 13px; color: #ffaa00;")
        gps_layout.addWidget(self.mother_gps)
        gps_layout.addWidget(self.drone_gps)
        gps_layout.addWidget(self.node1_gps)
        gps_layout.addWidget(self.node2_gps)
        gps_layout.addWidget(self.node3_gps)
        gps_group.setLayout(gps_layout)
        layout.addWidget(gps_group, 5, 2)

        # アラート
        alert_group = QGroupBox("⚠️ アラート")
        alert_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        alert_layout = QVBoxLayout()
        self.alert_label = QLabel("✅ 正常稼働中")
        self.alert_label.setStyleSheet("font-size: 14px; color: #00ff88;")
        self.db_stats = QLabel("DB: 0件")
        self.db_stats.setStyleSheet("font-size: 13px; color: #66ff66;")
        alert_layout.addWidget(self.alert_label)
        alert_layout.addWidget(self.db_stats)
        alert_group.setLayout(alert_layout)
        layout.addWidget(alert_group, 5, 3)

        # イベントログ
        log_group = QGroupBox("📋 イベントログ")
        log_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("background-color: #0a0a1a; color: #00ff88; font-family: monospace; font-size: 12px;")
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group, 6, 0, 1, 4)

        self.battery_mother.setValue(100)
        self.battery_drone.setValue(100)
        self.battery_node.setValue(100)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(1000)

        self.add_log("🔥 PHENIX Command Center v3.1 起動！")
        self.add_log("✅ MAVLink Bridge 接続完了")
        self.add_log("✅ LoRa Manager 初期化完了")
        self.add_log("✅ SQLite データベース稼働中")
        self.add_log("✅ 操作パネル準備完了")

    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def start_follow_mode(self):
        self.current_mode = "追従モード"
        self.mavlink.set_mode("FOLLOW")
        self.mode_label.setText("現在のモード: 🟢 追従モード")
        self.mode_label.setStyleSheet("font-size: 16px; color: #00ff88; font-weight: bold;")
        self.add_log("🟢 追従モード開始！ドローンが母艦を追従します")
        self.emergency = False

    def stop_follow_mode(self):
        self.current_mode = "ホバリング"
        self.mavlink.set_mode("LOITER")
        self.mode_label.setText("現在のモード: 🔴 追従解除（ホバリング）")
        self.mode_label.setStyleSheet("font-size: 16px; color: #ff4444; font-weight: bold;")
        self.add_log("🔴 追従解除！ドローンはホバリング中")

    def start_circle_mode(self):
        self.current_mode = "旋回モード"
        self.mavlink.set_mode("AUTO")
        self.mode_label.setText("現在のモード: 🔵 旋回モード")
        self.mode_label.setStyleSheet("font-size: 16px; color: #00aaff; font-weight: bold;")
        self.add_log("🔵 旋回モード開始！ドローンがエリアを旋回します")

    def start_return_mode(self):
        self.current_mode = "帰還モード"
        self.mavlink.set_mode("GUIDED")
        self.mode_label.setText("現在のモード: 🟡 帰還モード")
        self.mode_label.setStyleSheet("font-size: 16px; color: #ffaa00; font-weight: bold;")
        self.add_log("🟡 帰還モード開始！ドローンがドックに帰還します")

    def emergency_stop(self):
        self.emergency = True
        self.current_mode = "緊急停止"
        self.mavlink.disarm()
        self.mode_label.setText("現在のモード: ⛔ 緊急停止！")
        self.mode_label.setStyleSheet("font-size: 16px; color: #ff0000; font-weight: bold;")
        self.alert_label.setText("⛔ 緊急停止実行！")
        self.alert_label.setStyleSheet("font-size: 14px; color: #ff0000;")
        self.add_log("⛔ 緊急停止！全システム停止")

    def manual_drop(self):
        if self.node_count > 0:
            self.node_count -= 1
            self.node_count_label.setText(f"ノード残数: {self.node_count}個")
            self.add_log(f"🚀 手動ノード投下！残り{self.node_count}個")
        else:
            self.add_log("❌ ノード残数が0です！")
            self.alert_label.setText("❌ ノード残数0！")
            self.alert_label.setStyleSheet("font-size: 14px; color: #ff4444;")

    def update_display(self):
        if self.emergency:
            return

        rssi = random.randint(-95, -55)
        snr = random.uniform(-5, 10)
        self.rssi_label.setText(f"RSSI: {rssi} dBm")
        self.snr_label.setText(f"SNR: {snr:.1f} dB")
        self.rssi_graph.update_graph(rssi)

        event = self.lora.check_rssi(rssi)
        self.lora.save_lora_data(rssi, snr, "PHENIX データ", event)

        if rssi < -85:
            self.rssi_label.setStyleSheet("font-size: 18px; color: #ff4444;")
            self.countdown_value += 1
            remaining = 7 - self.countdown_value
            self.countdown_label.setText(f"⚠️ 投下まで: {remaining}秒...")
            self.alert_label.setText("⚠️ 電波弱化検知！")
            self.alert_label.setStyleSheet("font-size: 14px; color: #ff4444;")
            if self.countdown_value >= 7 and self.node_count > 0:
                self.node_count -= 1
                self.node_count_label.setText(f"ノード残数: {self.node_count}個")
                self.add_log(f"🚀 自動ノード投下！残り{self.node_count}個")
                self.countdown_value = 0
        else:
            self.rssi_label.setStyleSheet("font-size: 18px; color: #00ff88;")
            self.countdown_label.setText("投下まで: 待機中")
            self.countdown_value = 0
            if not self.emergency:
                self.alert_label.setText("✅ 正常稼働中")
                self.alert_label.setStyleSheet("font-size: 14px; color: #00ff88;")

        drone = self.mavlink.get_drone_telemetry()
        mother = self.mavlink.get_mother_telemetry()

        if drone:
            self.drone_mode.setText(f"モード: {drone['mode']}")
            self.drone_armed.setText(f"アーム: {'✅ ON' if drone['armed'] else '❌ OFF'}")
            self.drone_alt.setText(f"高度: {drone['altitude']:.1f} m")
            self.drone_speed.setText(f"速度: {drone['speed']:.1f} km/h")
            self.drone_heading.setText(f"方位: {drone['heading']:.0f} °")
            self.drone_sats.setText(f"衛星: {drone['satellites']} 機")
            self.battery_drone.setValue(drone['battery'])
            self.bat_drone_label.setText(f"ドローン: {drone['battery']}%")
            self.drone_gps.setText(f"ドローン: {drone['lat']:.4f}, {drone['lng']:.4f}")

        if mother:
            self.battery_mother.setValue(mother['battery'])
            self.bat_mother_label.setText(f"母艦: {mother['battery']}%")
            self.mother_gps.setText(f"母艦: {mother['lat']:.4f}, {mother['lng']:.4f}")
            self.mavlink.save_telemetry(drone, mother)

        temp = random.uniform(20, 35)
        humid = random.uniform(40, 80)
        pressure = random.uniform(1010, 1020)
        self.temperature.setText(f"気温: {temp:.1f} ℃")
        self.humidity.setText(f"湿度: {humid:.1f} %")
        self.pressure_label.setText(f"気圧: {pressure:.1f} hPa")

        stats = self.lora.get_stats()
        self.db_stats.setText(f"DB: {stats['total_records']}件記録済み")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PHENIXMain()
    window.show()
    sys.exit(app.exec())