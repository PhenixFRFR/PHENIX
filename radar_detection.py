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


class RadarTarget:
    """レーダーターゲット（人・物体）"""

    def __init__(self, x, y, target_type="human", speed=0.5):
        self.x = x
        self.y = y
        self.type = target_type
        self.speed = speed
        self.direction = random.uniform(0, 360)
        self.detected = False

    def move(self):
        """ターゲットを移動"""
        self.x += self.speed * math.cos(math.radians(self.direction))
        self.y += self.speed * math.sin(math.radians(self.direction))

        # 境界で反転
        if self.x < 0 or self.x > 600:
            self.direction = 180 - self.direction
        if self.y < 0 or self.y > 400:
            self.direction = 360 - self.direction

        # ランダムに方向変更
        if random.random() < 0.05:
            self.direction += random.uniform(-30, 30)


class LD2410Simulator:
    """LD2410 mmWaveレーダーシミュレーター"""

    def __init__(self, node_id, x, y, detection_range=6.0):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.detection_range = detection_range  # メートル
        self.scale = 50  # ピクセル/メートル
        self.targets = []
        self.detected_targets = []

    def add_target(self, target):
        self.targets.append(target)

    def scan(self):
        """レーダースキャン"""
        self.detected_targets = []
        for target in self.targets:
            dist = math.sqrt(
                (target.x - self.x)**2 + (target.y - self.y)**2
            ) / self.scale
            if dist <= self.detection_range:
                target.detected = True
                self.detected_targets.append({
                    'target': target,
                    'distance': dist,
                    'type': target.type,
                    'signal_strength': max(0, 100 - dist * 15)
                })
            else:
                target.detected = False
        return self.detected_targets


class RadarGraph(FigureCanvas):
    """レーダー表示グラフ"""

    def __init__(self):
        self.fig = Figure(figsize=(6, 4), facecolor='#0a0a1a')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#0a0a1a')
        self.ax.tick_params(colors='#00ff88')
        for spine in self.ax.spines.values():
            spine.set_color('#00ff88')
        super().__init__(self.fig)

    def update_radar(self, nodes, targets, detection_range=300):
        self.ax.clear()
        self.ax.set_facecolor('#0a0a1a')
        self.ax.set_xlim(0, 600)
        self.ax.set_ylim(0, 400)
        self.ax.tick_params(colors='#00ff88')
        for spine in self.ax.spines.values():
            spine.set_color('#00ff88')
        self.ax.set_title('レーダー検知マップ', color='#00ff88', fontsize=11)
        self.ax.set_xlabel('X (m)', color='#00ff88', fontsize=9)
        self.ax.set_ylabel('Y (m)', color='#00ff88', fontsize=9)

        # ノードの検知範囲を描画
        for node in nodes:
            circle = plt_circle(
                (node.x, node.y), detection_range,
                color='#00ff88', fill=True, alpha=0.05, linestyle='--'
            )
            self.ax.add_patch(circle)
            self.ax.plot(node.x, node.y, 'g^', markersize=12)
            self.ax.annotate(
                f'ノード{node.node_id}',
                (node.x, node.y), color='#00ff88',
                fontsize=8, ha='center', va='bottom'
            )

        # ターゲットを描画
        for target in targets:
            if target.detected:
                color = '#ff4444' if target.type == 'human' else '#ffaa00'
                marker = 'o' if target.type == 'human' else 's'
                self.ax.plot(target.x, target.y, marker, color=color, markersize=10)
                label = '👤人' if target.type == 'human' else '📦物体'
                self.ax.annotate(
                    label, (target.x, target.y),
                    color=color, fontsize=8, ha='center', va='bottom'
                )
            else:
                self.ax.plot(target.x, target.y, 'x', color='#333333', markersize=8)

        self.draw()


def plt_circle(center, radius, **kwargs):
    from matplotlib.patches import Circle
    return Circle(center, radius, **kwargs)


class RadarDetectionSystem(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("📡 PHENIX レーダー検知システム")
        self.setGeometry(100, 100, 1300, 850)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        self.base_lat = -33.2833
        self.base_lng = 149.1000
        self.map_file = os.path.expanduser("~/PHENIX/radar_map.html")
        self.running = False
        self.total_detections = 0

        # ノード設置（8個）
        self.nodes = [
            LD2410Simulator(1, 100, 100),
            LD2410Simulator(2, 300, 100),
            LD2410Simulator(3, 500, 100),
            LD2410Simulator(4, 100, 300),
            LD2410Simulator(5, 300, 300),
            LD2410Simulator(6, 500, 300),
            LD2410Simulator(7, 200, 200),
            LD2410Simulator(8, 400, 200),
        ]

        # ターゲット設置
        self.targets = [
            RadarTarget(150, 150, "human", 1.5),
            RadarTarget(350, 250, "human", 2.0),
            RadarTarget(450, 150, "object", 0.5),
        ]

        for node in self.nodes:
            for target in self.targets:
                node.add_target(target)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # 左パネル
        left_panel = QWidget()
        left_panel.setMaximumWidth(350)
        left_layout = QVBoxLayout(left_panel)

        title = QLabel("📡 PHENIX レーダー検知システム")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title)

        subtitle = QLabel("LD2410 mmWave シミュレーター")
        subtitle.setStyleSheet("font-size: 11px; color: #666666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(subtitle)

        # コントロール
        ctrl_group = QGroupBox("🎮 コントロール")
        ctrl_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        ctrl_layout = QVBoxLayout()

        self.btn_start = QPushButton("▶️ スキャン開始")
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
        self.btn_start.clicked.connect(self.toggle_scan)
        ctrl_layout.addWidget(self.btn_start)

        btn_add_human = QPushButton("➕ 人を追加")
        btn_add_human.setStyleSheet("""
            QPushButton {
                background-color: #330000;
                color: #ff4444;
                border: 2px solid #ff4444;
                padding: 8px;
                font-size: 13px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #550000; }
        """)
        btn_add_human.clicked.connect(self.add_human)
        ctrl_layout.addWidget(btn_add_human)

        btn_add_object = QPushButton("📦 物体を追加")
        btn_add_object.setStyleSheet("""
            QPushButton {
                background-color: #333300;
                color: #ffaa00;
                border: 2px solid #ffaa00;
                padding: 8px;
                font-size: 13px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #555500; }
        """)
        btn_add_object.clicked.connect(self.add_object)
        ctrl_layout.addWidget(btn_add_object)

        btn_clear = QPushButton("🗑️ ターゲットクリア")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #003333;
                color: #00ffff;
                border: 2px solid #00ffff;
                padding: 8px;
                font-size: 13px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #005555; }
        """)
        btn_clear.clicked.connect(self.clear_targets)
        ctrl_layout.addWidget(btn_clear)

        btn_map = QPushButton("🗺️ 地図を開く")
        btn_map.setStyleSheet("""
            QPushButton {
                background-color: #440044;
                color: #ff66ff;
                border: 2px solid #ff66ff;
                padding: 8px;
                font-size: 13px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #660066; }
        """)
        btn_map.clicked.connect(self.open_map)
        ctrl_layout.addWidget(btn_map)

        ctrl_group.setLayout(ctrl_layout)
        left_layout.addWidget(ctrl_group)

        # 検知範囲スライダー
        range_group = QGroupBox("📏 検知範囲")
        range_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        range_layout = QVBoxLayout()
        self.range_slider = QSlider(Qt.Orientation.Horizontal)
        self.range_slider.setMinimum(100)
        self.range_slider.setMaximum(500)
        self.range_slider.setValue(300)
        self.range_label = QLabel("300 px（約6m）")
        self.range_label.setStyleSheet("color: #00aaff; font-size: 13px;")
        self.range_slider.valueChanged.connect(
            lambda v: self.range_label.setText(f"{v} px（約{v//50}m）")
        )
        range_layout.addWidget(self.range_slider)
        range_layout.addWidget(self.range_label)
        range_group.setLayout(range_layout)
        left_layout.addWidget(range_group)

        # ノード状態
        node_group = QGroupBox("📡 ノード状態（8個）")
        node_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        node_layout = QVBoxLayout()
        self.node_labels = []
        for i in range(8):
            label = QLabel(f"ノード{i+1}: 待機中")
            label.setStyleSheet("font-size: 11px; color: #444444;")
            node_layout.addWidget(label)
            self.node_labels.append(label)
        node_group.setLayout(node_layout)
        left_layout.addWidget(node_group)

        # 統計
        stats_group = QGroupBox("📊 統計")
        stats_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        stats_layout = QVBoxLayout()
        self.total_label = QLabel("総検知数: 0")
        self.total_label.setStyleSheet("font-size: 14px; color: #00ff88;")
        self.human_label = QLabel("人体検知: 0")
        self.human_label.setStyleSheet("font-size: 14px; color: #ff4444;")
        self.object_label = QLabel("物体検知: 0")
        self.object_label.setStyleSheet("font-size: 14px; color: #ffaa00;")
        self.alert_label = QLabel("✅ 異常なし")
        self.alert_label.setStyleSheet("font-size: 13px; color: #00ff88; font-weight: bold;")
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.human_label)
        stats_layout.addWidget(self.object_label)
        stats_layout.addWidget(self.alert_label)
        stats_group.setLayout(stats_layout)
        left_layout.addWidget(stats_group)

        layout.addWidget(left_panel)

        # 右パネル
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.radar_graph = RadarGraph()
        right_layout.addWidget(self.radar_graph)

        self.log_text = QTextEdit()
        self.log_text.setStyleSheet(
            "background-color: #050510; color: #00ff88; font-family: monospace; font-size: 11px;"
        )
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        right_layout.addWidget(self.log_text)

        layout.addWidget(right_panel)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_scan)

        self.update_map()
        self.log("📡 PHENIX レーダー検知システム起動！")
        self.log(f"✅ LD2410ノード {len(self.nodes)}個 配置完了")
        self.log(f"✅ ターゲット {len(self.targets)}個 配置完了")
        self.log("「スキャン開始」ボタンでスキャンを開始します")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def toggle_scan(self):
        self.running = not self.running
        if self.running:
            self.timer.start(200)
            self.btn_start.setText("⏹️ スキャン停止")
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
            self.log("▶️ レーダースキャン開始！")
        else:
            self.timer.stop()
            self.btn_start.setText("▶️ スキャン開始")
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
            self.log("⏹️ スキャン停止")

    def add_human(self):
        x = random.randint(50, 550)
        y = random.randint(50, 350)
        target = RadarTarget(x, y, "human", random.uniform(1, 3))
        self.targets.append(target)
        for node in self.nodes:
            node.add_target(target)
        self.log(f"➕ 人を追加（{x}, {y}）")

    def add_object(self):
        x = random.randint(50, 550)
        y = random.randint(50, 350)
        target = RadarTarget(x, y, "object", random.uniform(0, 0.5))
        self.targets.append(target)
        for node in self.nodes:
            node.add_target(target)
        self.log(f"📦 物体を追加（{x}, {y}）")

    def clear_targets(self):
        self.targets = []
        for node in self.nodes:
            node.targets = []
        self.log("🗑️ ターゲットをクリア")

    def update_scan(self):
        for target in self.targets:
            target.move()

        detection_range = self.range_slider.value()
        total_detected = 0
        human_detected = 0
        object_detected = 0

        for i, node in enumerate(self.nodes):
            detected = node.scan()
            if detected:
                self.node_labels[i].setText(
                    f"ノード{i+1}: 🔴 検知({len(detected)})"
                )
                self.node_labels[i].setStyleSheet("font-size: 11px; color: #ff4444;")
                total_detected += len(detected)
                for det in detected:
                    if det['type'] == 'human':
                        human_detected += 1
                    else:
                        object_detected += 1
            else:
                self.node_labels[i].setText(f"ノード{i+1}: ✅ 待機中")
                self.node_labels[i].setStyleSheet("font-size: 11px; color: #00ff88;")

        self.total_detections = total_detected
        self.total_label.setText(f"総検知数: {total_detected}")
        self.human_label.setText(f"人体検知: {human_detected}")
        self.object_label.setText(f"物体検知: {object_detected}")

        if human_detected > 0:
            self.alert_label.setText(f"⚠️ 人体{human_detected}人検知！")
            self.alert_label.setStyleSheet(
                "font-size: 13px; color: #ff4444; font-weight: bold;"
            )
        elif object_detected > 0:
            self.alert_label.setText(f"📦 物体{object_detected}個検知")
            self.alert_label.setStyleSheet(
                "font-size: 13px; color: #ffaa00; font-weight: bold;"
            )
        else:
            self.alert_label.setText("✅ 異常なし")
            self.alert_label.setStyleSheet("font-size: 13px; color: #00ff88;")

        self.radar_graph.update_radar(self.nodes, self.targets, detection_range)

        if human_detected > 0 and random.random() < 0.05:
            self.log(f"⚠️ 人体{human_detected}人検知！レーダーネットワーク稼働中")
            self.update_map()

    def update_map(self):
        m = folium.Map(
            location=[self.base_lat, self.base_lng],
            zoom_start=15,
            tiles='CartoDB positron'
        )

        node_positions = [
            [self.base_lat + (n.y - 200) * 0.000009,
             self.base_lng + (n.x - 300) * 0.000009]
            for n in self.nodes
        ]

        for i, (node, pos) in enumerate(zip(self.nodes, node_positions)):
            folium.Marker(
                pos,
                tooltip=f"📡 ノード{i+1}",
                icon=folium.Icon(color='green', icon='wifi', prefix='fa')
            ).add_to(m)
            folium.Circle(
                pos, radius=6,
                color='#00ff88', fill=True, fill_opacity=0.1
            ).add_to(m)

        for target in self.targets:
            if target.detected:
                pos = [
                    self.base_lat + (target.y - 200) * 0.000009,
                    self.base_lng + (target.x - 300) * 0.000009
                ]
                color = 'red' if target.type == 'human' else 'orange'
                icon_name = 'user' if target.type == 'human' else 'cube'
                label = '👤 人体検知' if target.type == 'human' else '📦 物体検知'
                folium.Marker(
                    pos,
                    tooltip=label,
                    icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
                ).add_to(m)

        m.save(self.map_file)

    def open_map(self):
        subprocess.Popen(['firefox', self.map_file])
        self.log("🌐 地図をFirefoxで開きました")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RadarDetectionSystem()
    window.show()
    sys.exit(app.exec())