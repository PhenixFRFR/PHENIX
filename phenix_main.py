import sys
import random
import sqlite3
from datetime import datetime
from threading import Thread
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
        self.setWindowTitle("🔥 PHENIX Command Center v3.0 - 統合システム")
        self.setGeometry(100, 100, 1400, 950)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        self.lora = LoRaManager()
        self.mavlink = MAVLinkBridge()
        self.mavlink.connect()

        self.node_count = 3
        self.countdown_value = 0

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QGridLayout(main_widget)

        # タイトル
        title = QLabel("🔥 PHENIX Command Center v3.0")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title, 0, 0, 1, 4)

        # 接続状態
        self.connection_status = QLabel("🔗 MAVLink: 接続中 | LoRa: 待機中 | DB: 稼働中")
        self.connection_status.setStyleSheet("font-size: 12px; color: #00aaff;")
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.connection_status, 1, 0, 1, 4)

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
        layout.addWidget(rssi_group, 2, 0)

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
        layout.addWidget(battery_group, 2, 1)

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
        layout.addWidget(drone_group, 2, 2)

        # センサーパネル
        sensor_group = QGroupBox("🌡️ センサー")
        sensor_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        sensor_layout = QVBoxLayout()
        self.temperature = QLabel("気温: --- ℃")
        self.temperature.setStyleSheet("font-size: 14px; color: #ff6666;")
        self.humidity = QLabel("湿度: --- %")
        self.humidity.setStyleSheet("font-size: 14px; color: #66aaff;")
        self.pressure = QLabel("気圧: --- hPa")
        self.pressure.setStyleSheet("font-size: 14px; color: #66ff66;")
        self.radar_status = QLabel("レーダー: 待機中")
        self.radar_status.setStyleSheet("font-size: 14px; color: #ffaa00;")
        self.uwb_status = QLabel("UWB: 待機中")
        self.uwb_status.setStyleSheet("font-size: 14px; color: #aa66ff;")
        self.thermal_status = QLabel("サーマル: 待機中")
        self.thermal_status.setStyleSheet("font-size: 14px; color: #ff6666;")
        sensor_layout.addWidget(self.temperature)
        sensor_layout.addWidget(self.humidity)
        sensor_layout.addWidget(self.pressure)
        sensor_layout.addWidget(self.radar_status)
        sensor_layout.addWidget(self.uwb_status)
        sensor_layout.addWidget(self.thermal_status)
        sensor_group.setLayout(sensor_layout)
        layout.addWidget(sensor_group, 2, 3)

        # RSSIグラフ
        self.rssi_graph = RSSIGraph()
        layout.addWidget(self.rssi_graph, 3, 0, 1, 2)

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
        layout.addWidget(gps_group, 3, 2)

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
        layout.addWidget(alert_group, 3, 3)

        # イベントログ
        log_group = QGroupBox("📋 イベントログ")
        log_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet(
            "background-color: #0a0a1a; color: #00ff88; font-family: monospace; font-size: 12px;"
        )
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group, 4, 0, 1, 4)

        self.battery_mother.setValue(100)
        self.battery_drone.setValue(100)
        self.battery_node.setValue(100)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(1000)

        self.add_log("🔥 PHENIX Command Center v3.0 起動！")
        self.add_log("✅ MAVLink Bridge 接続完了")
        self.add_log("✅ LoRa Manager 初期化完了")
        self.add_log("✅ SQLite データベース稼働中")

    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def update_display(self):
        # LoRaデータ更新
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
            self.countdown_label.setText(f"⚠️ 投下まで: {7 - self.countdown_value}秒...")
            self.alert_label.setText("⚠️ 電波弱化検知！")
            self.alert_label.setStyleSheet("font-size: 14px; color: #ff4444;")
            if self.countdown_value >= 7 and self.node_count > 0:
                self.node_count -= 1
                self.node_count_label.setText(f"ノード残数: {self.node_count}個")
                self.add_log(f"🚀 ノード投下！残り{self.node_count}個")
                self.countdown_value = 0
        else:
            self.rssi_label.setStyleSheet("font-size: 18px; color: #00ff88;")
            self.countdown_label.setText("投下まで: 待機中")
            self.countdown_value = 0
            self.alert_label.setText("✅ 正常稼働中")
            self.alert_label.setStyleSheet("font-size: 14px; color: #00ff88;")

        # MAVLinkデータ更新
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

        # センサーデータ
        temp = random.uniform(20, 35)
        humid = random.uniform(40, 80)
        pressure = random.uniform(1010, 1020)
        self.temperature.setText(f"気温: {temp:.1f} ℃")
        self.humidity.setText(f"湿度: {humid:.1f} %")
        self.pressure.setText(f"気圧: {pressure:.1f} hPa")

        # DB統計
        stats = self.lora.get_stats()
        self.db_stats.setText(f"DB: {stats['total_records']}件記録済み")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PHENIXMain()
    window.show()
    sys.exit(app.exec())