import sys
import os
import subprocess
import folium
import random
import math
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


class PHENIXMapViewer(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🗺️ PHENIX マップビューア")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        # 初期座標（オレンジ・オーストラリア）
        self.base_lat = -33.2833
        self.base_lng = 149.1000

        self.mother_pos = [self.base_lat, self.base_lng]
        self.drone_pos = [self.base_lat + 0.001, self.base_lng + 0.001]
        self.nodes = []
        self.node_radius = 500
        self.running = False
        self.map_file = os.path.expanduser("~/PHENIX/phenix_map.html")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # タイトル
        title = QLabel("🗺️ PHENIX リアルタイムマップ")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ボタンパネル
        btn_layout = QHBoxLayout()

        self.btn_start = QPushButton("▶️ シミュレーション開始")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #004400;
                color: #00ff88;
                border: 2px solid #00ff88;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #006600; }
        """)
        self.btn_start.clicked.connect(self.start_simulation)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹️ 停止")
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #440000;
                color: #ff4444;
                border: 2px solid #ff4444;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #660000; }
        """)
        self.btn_stop.clicked.connect(self.stop_simulation)
        btn_layout.addWidget(self.btn_stop)

        self.btn_drop = QPushButton("🚀 ノード投下")
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
        """)
        self.btn_drop.clicked.connect(self.drop_node)
        btn_layout.addWidget(self.btn_drop)

        self.btn_clear = QPushButton("🗑️ ノードクリア")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #444400;
                color: #ffaa00;
                border: 2px solid #ffaa00;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #666600; }
        """)
        self.btn_clear.clicked.connect(self.clear_nodes)
        btn_layout.addWidget(self.btn_clear)

        self.btn_open = QPushButton("🌐 ブラウザで開く")
        self.btn_open.setStyleSheet("""
            QPushButton {
                background-color: #004444;
                color: #00ffff;
                border: 2px solid #00ffff;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #006666; }
        """)
        self.btn_open.clicked.connect(self.open_in_browser)
        btn_layout.addWidget(self.btn_open)

        # 通信圏半径スライダー
        radius_label = QLabel("通信圏半径:")
        radius_label.setStyleSheet("color: #00ff88; font-size: 13px;")
        btn_layout.addWidget(radius_label)

        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setMinimum(100)
        self.radius_slider.setMaximum(2000)
        self.radius_slider.setValue(500)
        self.radius_slider.setMaximumWidth(200)
        self.radius_slider.valueChanged.connect(self.update_radius)
        btn_layout.addWidget(self.radius_slider)

        self.radius_value_label = QLabel("500 m")
        self.radius_value_label.setStyleSheet("color: #00aaff; font-size: 14px; font-weight: bold;")
        btn_layout.addWidget(self.radius_value_label)

        layout.addLayout(btn_layout)

        # 状態表示
        status_layout = QHBoxLayout()
        self.mother_label = QLabel("🔴 母艦: 待機中")
        self.mother_label.setStyleSheet("font-size: 14px; color: #00ff88;")
        status_layout.addWidget(self.mother_label)

        self.drone_label = QLabel("🔵 ドローン: 待機中")
        self.drone_label.setStyleSheet("font-size: 14px; color: #00aaff;")
        status_layout.addWidget(self.drone_label)

        self.node_label = QLabel("🟡 ノード: 0個")
        self.node_label.setStyleSheet("font-size: 14px; color: #ffaa00;")
        status_layout.addWidget(self.node_label)

        self.coverage_label = QLabel("📡 通信カバレッジ: 0 km²")
        self.coverage_label.setStyleSheet("font-size: 14px; color: #ff66ff;")
        status_layout.addWidget(self.coverage_label)

        layout.addLayout(status_layout)

        # ログエリア
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("background-color: #0a0a1a; color: #00ff88; font-family: monospace; font-size: 12px;")
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # タイマー
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)

        self.update_map()
        self.log("🔥 PHENIX マップビューア起動！")
        self.log("🌐 「ブラウザで開く」ボタンで地図を確認できます")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def update_radius(self, value):
        self.node_radius = value
        self.radius_value_label.setText(f"{value} m")
        self.update_map()

    def create_map(self):
        m = folium.Map(
            location=self.mother_pos,
            zoom_start=14,
            tiles='CartoDB positron'
        )

        # 母艦マーカー
        folium.Marker(
            self.mother_pos,
            popup=f"母艦<br>Lat: {self.mother_pos[0]:.4f}<br>Lng: {self.mother_pos[1]:.4f}",
            tooltip="🔴 母艦",
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(m)

        # 母艦の通信圏
        folium.Circle(
            self.mother_pos,
            radius=self.node_radius,
            color='#00ff88',
            fill=True,
            fill_color='#00ff88',
            fill_opacity=0.1,
            popup=f"母艦通信圏 {self.node_radius}m"
        ).add_to(m)

        # ドローンマーカー
        folium.Marker(
            self.drone_pos,
            popup=f"ドローン<br>Lat: {self.drone_pos[0]:.4f}<br>Lng: {self.drone_pos[1]:.4f}",
            tooltip="🔵 ドローン",
            icon=folium.Icon(color='blue', icon='plane', prefix='fa')
        ).add_to(m)

        # ノードマーカーと通信圏
        for i, node in enumerate(self.nodes):
            folium.Marker(
                node,
                popup=f"ノード{i+1}<br>Lat: {node[0]:.4f}<br>Lng: {node[1]:.4f}",
                tooltip=f"🟡 ノード{i+1}",
                icon=folium.Icon(color='orange', icon='wifi', prefix='fa')
            ).add_to(m)

            folium.Circle(
                node,
                radius=self.node_radius,
                color='#ffaa00',
                fill=True,
                fill_color='#ffaa00',
                fill_opacity=0.1,
                popup=f"ノード{i+1}通信圏 {self.node_radius}m"
            ).add_to(m)

        return m

    def update_map(self):
        m = self.create_map()
        m.save(self.map_file)

        area = math.pi * (self.node_radius/1000)**2 * (len(self.nodes) + 1)
        self.coverage_label.setText(f"📡 通信カバレッジ: {area:.2f} km²")
        self.node_label.setText(f"🟡 ノード: {len(self.nodes)}個")

    def open_in_browser(self):
        subprocess.Popen(['firefox', self.map_file])
        self.log("🌐 Firefoxで地図を開きました！")

    def start_simulation(self):
        self.running = True
        self.timer.start(2000)
        self.btn_start.setText("▶️ 実行中...")
        self.mother_label.setText("🔴 母艦: 走行中")
        self.drone_label.setText("🔵 ドローン: 追従中")
        self.log("▶️ シミュレーション開始！")
        self.open_in_browser()

    def stop_simulation(self):
        self.running = False
        self.timer.stop()
        self.btn_start.setText("▶️ シミュレーション開始")
        self.mother_label.setText("🔴 母艦: 停止中")
        self.drone_label.setText("🔵 ドローン: ホバリング中")
        self.log("⏹️ シミュレーション停止")

    def update_simulation(self):
        self.mother_pos[0] += random.uniform(-0.0003, 0.0003)
        self.mother_pos[1] += random.uniform(0.0001, 0.0004)

        self.drone_pos[0] = self.mother_pos[0] + random.uniform(-0.0005, 0.0005)
        self.drone_pos[1] = self.mother_pos[1] + random.uniform(-0.0005, 0.0005)

        self.mother_label.setText(f"🔴 母艦: {self.mother_pos[0]:.4f}, {self.mother_pos[1]:.4f}")
        self.drone_label.setText(f"🔵 ドローン: {self.drone_pos[0]:.4f}, {self.drone_pos[1]:.4f}")

        self.update_map()
        self.log(f"📍 母艦移動: {self.mother_pos[0]:.4f}, {self.mother_pos[1]:.4f}")

    def drop_node(self):
        node_pos = [
            self.mother_pos[0] + random.uniform(-0.001, 0.001),
            self.mother_pos[1] + random.uniform(-0.001, 0.001)
        ]
        self.nodes.append(node_pos)
        self.update_map()
        self.log(f"🚀 ノード{len(self.nodes)}投下！位置: {node_pos[0]:.4f}, {node_pos[1]:.4f}")
        if self.running:
            self.open_in_browser()

    def clear_nodes(self):
        self.nodes = []
        self.update_map()
        self.log("🗑️ ノードをクリアしました")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PHENIXMapViewer()
    window.show()
    sys.exit(app.exec())