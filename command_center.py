
import sys
import random
import csv
import os
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class RSSIGraph(FigureCanvas):

    def __init__(self):
        self.fig = Figure(figsize=(5, 2), facecolor='#1a1a2e')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#0a0a1a')
        self.ax.tick_params(colors='#00ff88')
        self.ax.spines['bottom'].set_color('#00ff88')
        self.ax.spines['top'].set_color('#00ff88')
        self.ax.spines['right'].set_color('#00ff88')
        self.ax.spines['left'].set_color('#00ff88')
        self.ax.set_ylim(-120, -40)
        self.ax.set_title('RSSI履歴', color='#00ff88')
        self.ax.axhline(y=-85, color='#ff4444', linestyle='--', label='投下閾値')
        self.ax.legend(facecolor='#1a1a2e', labelcolor='#00ff88')
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
        self.ax.spines['bottom'].set_color('#00ff88')
        self.ax.spines['top'].set_color('#00ff88')
        self.ax.spines['right'].set_color('#00ff88')
        self.ax.spines['left'].set_color('#00ff88')
        self.ax.axhline(y=-85, color='#ff4444', linestyle='--', label='投下閾値 -85dBm')
        colors = ['#ff4444' if r < -85 else '#00ff88' for r in self.rssi_data]
        self.ax.bar(range(len(self.rssi_data)), self.rssi_data, color=colors, alpha=0.7)
        self.ax.legend(facecolor='#1a1a2e', labelcolor='#00ff88')
        self.draw()


class PHENIXCommandCenter(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PHENIX Command Center v2.0")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")
        self.countdown_value = 0
        self.node_count = 3
        self.log_data = []

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QGridLayout(main_widget)

        title = QLabel("🔥 PHENIX Command Center v2.0")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title, 0, 0, 1, 4)

        rssi_group = QGroupBox("📡 RSSI 電波強度")
        rssi_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        rssi_layout = QVBoxLayout()
        self.rssi_label = QLabel("RSSI: --- dBm")
        self.rssi_label.setStyleSheet("font-size: 20px; color: #00ff88;")
        self.countdown_label = QLabel("投下まで: 待機中")
        self.countdown_label.setStyleSheet("font-size: 16px; color: #ffaa00;")
        self.comm_mode = QLabel("通信モード: LoRa")
        self.comm_mode.setStyleSheet("font-size: 16px; color: #00aaff;")
        self.packet_loss = QLabel("パケットロス: 0%")
        self.packet_loss.setStyleSheet("font-size: 16px; color: #ff6666;")
        rssi_layout.addWidget(self.rssi_label)
        rssi_layout.addWidget(self.countdown_label)
        rssi_layout.addWidget(self.comm_mode)
        rssi_layout.addWidget(self.packet_loss)
        rssi_group.setLayout(rssi_layout)
        layout.addWidget(rssi_group, 1, 0)

        battery_group = QGroupBox("🔋 バッテリー残量")
        battery_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        battery_layout = QVBoxLayout()
        self.battery_mother = QProgressBar()
        self.battery_mother.setStyleSheet("QProgressBar { border: 1px solid #00ff88; } QProgressBar::chunk { background-color: #00ff88; }")
        self.battery_drone = QProgressBar()
        self.battery_drone.setStyleSheet("QProgressBar { border: 1px solid #00aaff; } QProgressBar::chunk { background-color: #00aaff; }")
        self.battery_node = QProgressBar()
        self.battery_node.setStyleSheet("QProgressBar { border: 1px solid #ffaa00; } QProgressBar::chunk { background-color: #ffaa00; }")
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
        layout.addWidget(battery_group, 1, 1)

        status_group = QGroupBox("🚁 システム状態")
        status_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        status_layout = QVBoxLayout()
        self.drone_status = QLabel("ドローン: 待機中")
        self.drone_status.setStyleSheet("font-size: 16px; color: #00ff88;")
        self.mother_status = QLabel("母艦: 待機中")
        self.mother_status.setStyleSheet("font-size: 16px; color: #00ff88;")
        self.node_count_label = QLabel("ノード残数: 3個")
        self.node_count_label.setStyleSheet("font-size: 16px; color: #ffaa00;")
        self.altitude = QLabel("高度: --- m")
        self.altitude.setStyleSheet("font-size: 16px; color: #00aaff;")
        self.speed_label = QLabel("速度: --- km/h")
        self.speed_label.setStyleSheet("font-size: 16px; color: #00aaff;")
        self.heading = QLabel("方位: --- °")
        self.heading.setStyleSheet("font-size: 16px; color: #aa66ff;")
        status_layout.addWidget(self.drone_status)
        status_layout.addWidget(self.mother_status)
        status_layout.addWidget(self.node_count_label)
        status_layout.addWidget(self.altitude)
        status_layout.addWidget(self.speed_label)
        status_layout.addWidget(self.heading)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group, 1, 2)

        sensor_group = QGroupBox("🌡️ センサーデータ")
        sensor_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        sensor_layout = QVBoxLayout()
        self.temperature = QLabel("気温: --- ℃")
        self.temperature.setStyleSheet("font-size: 16px; color: #ff6666;")
        self.humidity = QLabel("湿度: --- %")
        self.humidity.setStyleSheet("font-size: 16px; color: #66aaff;")
        self.pressure = QLabel("気圧: --- hPa")
        self.pressure.setStyleSheet("font-size: 16px; color: #66ff66;")
        self.radar_status = QLabel("レーダー: 待機中")
        self.radar_status.setStyleSheet("font-size: 16px; color: #ffaa00;")
        self.uwb_status = QLabel("UWB: 待機中")
        self.uwb_status.setStyleSheet("font-size: 16px; color: #aa66ff;")
        self.thermal_status = QLabel("サーマル: 待機中")
        self.thermal_status.setStyleSheet("font-size: 16px; color: #ff6666;")
        sensor_layout.addWidget(self.temperature)
        sensor_layout.addWidget(self.humidity)
        sensor_layout.addWidget(self.pressure)
        sensor_layout.addWidget(self.radar_status)
        sensor_layout.addWidget(self.uwb_status)
        sensor_layout.addWidget(self.thermal_status)
        sensor_group.setLayout(sensor_layout)
        layout.addWidget(sensor_group, 1, 3)

        self.rssi_graph = RSSIGraph()
        layout.addWidget(self.rssi_graph, 2, 0, 1, 2)

        gps_group = QGroupBox("📍 GPS位置情報")
        gps_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        gps_layout = QVBoxLayout()
        self.mother_gps = QLabel("母艦: ---, ---")
        self.mother_gps.setStyleSheet("font-size: 14px; color: #00ff88;")
        self.drone_gps = QLabel("ドローン: ---, ---")
        self.drone_gps.setStyleSheet("font-size: 14px; color: #00aaff;")
        self.node1_gps = QLabel("ノード1: ---, ---")
        self.node1_gps.setStyleSheet("font-size: 14px; color: #ffaa00;")
        self.node2_gps = QLabel("ノード2: ---, ---")
        self.node2_gps.setStyleSheet("font-size: 14px; color: #ffaa00;")
        self.node3_gps = QLabel("ノード3: ---, ---")
        self.node3_gps.setStyleSheet("font-size: 14px; color: #ffaa00;")
        gps_layout.addWidget(self.mother_gps)
        gps_layout.addWidget(self.drone_gps)
        gps_layout.addWidget(self.node1_gps)
        gps_layout.addWidget(self.node2_gps)
        gps_layout.addWidget(self.node3_gps)
        gps_group.setLayout(gps_layout)
        layout.addWidget(gps_group, 2, 2)

        alert_group = QGroupBox("⚠️ アラート")
        alert_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        alert_layout = QVBoxLayout()
        self.alert_label = QLabel("✅ 正常稼働中")
        self.alert_label.setStyleSheet("font-size: 16px; color: #00ff88;")
        alert_layout.addWidget(self.alert_label)
        alert_group.setLayout(alert_layout)
        layout.addWidget(alert_group, 2, 3)

        log_group = QGroupBox("📋 イベントログ")
        log_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("background-color: #0a0a1a; color: #00ff88; font-family: monospace;")
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group, 3, 0, 1, 4)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(1000)

        self.add_log("🔥 PHENIX Command Center v2.0 起動！")
        self.add_log("✅ システム初期化完了")
        self.add_log("📊 CSVログ記録開始")

        self.battery_mother.setValue(100)
        self.battery_drone.setValue(100)
        self.battery_node.setValue(100)

        self.csv_file = f"PHENIX_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['時刻', 'RSSI', '母艦バッテリー', 'ドローンバッテリー', '気温', '湿度', '気圧', 'イベント'])

    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def save_csv(self, rssi, temp, humid, pressure, event=""):
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                rssi,
                self.battery_mother.value(),
                self.battery_drone.value(),
                f"{temp:.1f}",
                f"{humid:.1f}",
                f"{pressure:.1f}",
                event
            ])

    def update_display(self):
        rssi = random.randint(-95, -55)
        self.rssi_label.setText(f"RSSI: {rssi} dBm")
        self.rssi_graph.update_graph(rssi)

        event = ""
        if rssi < -85:
            self.rssi_label.setStyleSheet("font-size: 20px; color: #ff4444;")
            if self.countdown_value == 0:
                self.countdown_value = 7
            self.countdown_value -= 1
            self.countdown_label.setText(f"⚠️ 投下まで: {self.countdown_value}秒...")
            self.alert_label.setText("⚠️ 電波弱化検知！")
            self.alert_label.setStyleSheet("font-size: 16px; color: #ff4444;")
            if self.countdown_value == 0 and self.node_count > 0:
                self.node_count -= 1
                self.node_count_label.setText(f"ノード残数: {self.node_count}個")
                self.add_log(f"🚀 ノード投下！残り{self.node_count}個")
                event = "ノード投下"
                self.countdown_value = 0
        else:
            self.rssi_label.setStyleSheet("font-size: 20px; color: #00ff88;")
            self.countdown_label.setText("投下まで: 待機中")
            self.countdown_value = 0
            self.alert_label.setText("✅ 正常稼働中")
            self.alert_label.setStyleSheet("font-size: 16px; color: #00ff88;")

        mother_bat = self.battery_mother.value()
        self.bat_mother_label.setText(f"母艦: {mother_bat}%")
        drone_bat = self.battery_drone.value()
        self.bat_drone_label.setText(f"ドローン: {drone_bat}%")

        temp = random.uniform(20, 35)
        humid = random.uniform(40, 80)
        pressure = random.uniform(1010, 1020)
        alt = random.uniform(10, 50)
        spd = random.uniform(0, 30)
        hdg = random.uniform(0, 360)

        self.temperature.setText(f"気温: {temp:.1f} ℃")
        self.humidity.setText(f"湿度: {humid:.1f} %")
        self.pressure.setText(f"気圧: {pressure:.1f} hPa")
        self.altitude.setText(f"高度: {alt:.1f} m")
        self.speed_label.setText(f"速度: {spd:.1f} km/h")
        self.heading.setText(f"方位: {hdg:.0f} °")

        lat = 33.8688 + random.uniform(-0.001, 0.001)
        lng = 151.2093 + random.uniform(-0.001, 0.001)
        self.mother_gps.setText(f"母艦: {lat:.4f}, {lng:.4f}")
        self.drone_gps.setText(f"ドローン: {lat+0.001:.4f}, {lng+0.001:.4f}")

        self.save_csv(rssi, temp, humid, pressure, event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PHENIXCommandCenter()
    window.show()
    sys.exit(app.exec())
