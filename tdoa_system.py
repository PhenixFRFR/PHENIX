import sys
import os
import math
import random
import subprocess
import folium
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


SPEED_OF_LIGHT = 299792458  # m/s
LORA_SPEED = 300000  # LoRaの電波速度（簡略化）


class TDOANode:
    """TDOAノード"""

    def __init__(self, node_id, x, y, lat, lng):
        self.id = node_id
        self.x = x
        self.y = y
        self.lat = lat
        self.lng = lng
        self.receive_time = 0
        self.active = True

    def receive_signal(self, source_x, source_y, base_time):
        """信号受信時刻を計算"""
        dist = math.sqrt((self.x - source_x)**2 + (self.y - source_y)**2)
        # 距離に応じた遅延時間（マイクロ秒）
        delay = dist / LORA_SPEED * 1000000
        noise = random.gauss(0, 0.5)  # ノイズ追加
        self.receive_time = base_time + delay + noise
        return self.receive_time


def tdoa_locate(nodes, source_x, source_y):
    """
    TDOAアルゴリズムで発信源を推定
    最小二乗法を使用
    """
    if len(nodes) < 3:
        return None, None, float('inf')

    base_node = nodes[0]
    estimates = []

    for i in range(1, len(nodes)):
        node = nodes[i]
        tdoa = node.receive_time - base_node.receive_time
        dist_diff = tdoa * LORA_SPEED / 1000000

        # 双曲線の交点を求める（簡略版）
        dx = node.x - base_node.x
        dy = node.y - base_node.y
        dist_base = math.sqrt(base_node.x**2 + base_node.y**2)

        # 推定位置
        est_x = base_node.x + dx / 2 + dist_diff * dx / (2 * math.sqrt(dx**2 + dy**2))
        est_y = base_node.y + dy / 2 + dist_diff * dy / (2 * math.sqrt(dx**2 + dy**2))
        estimates.append((est_x, est_y))

    if estimates:
        avg_x = sum(e[0] for e in estimates) / len(estimates)
        avg_y = sum(e[1] for e in estimates) / len(estimates)

        # 誤差計算
        error = math.sqrt((avg_x - source_x)**2 + (avg_y - source_y)**2)
        return avg_x, avg_y, error

    return None, None, float('inf')


class TDOAGraph(FigureCanvas):

    def __init__(self):
        self.fig = Figure(figsize=(7, 5), facecolor='#1a1a2e')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#0a0a1a')
        super().__init__(self.fig)

    def update_plot(self, nodes, source_pos, estimated_pos, hyperbolas=None):
        self.ax.clear()
        self.ax.set_facecolor('#0a0a1a')
        self.ax.tick_params(colors='#00ff88')
        for spine in self.ax.spines.values():
            spine.set_color('#00ff88')
        self.ax.set_xlim(0, 600)
        self.ax.set_ylim(0, 400)
        self.ax.set_title('TDOA位置特定マップ', color='#00ff88', fontsize=11)
        self.ax.set_xlabel('X (m)', color='#00ff88', fontsize=9)
        self.ax.set_ylabel('Y (m)', color='#00ff88', fontsize=9)
        self.ax.grid(color='#222222', linestyle='--', alpha=0.5)

        # ノードを描画
        for node in nodes:
            if node.active:
                self.ax.plot(node.x, node.y, '^', color='#00ff88', markersize=12)
                self.ax.annotate(
                    f'N{node.id}\n({node.receive_time:.1f}μs)',
                    (node.x, node.y),
                    color='#00ff88', fontsize=7,
                    ha='center', va='bottom'
                )
                # ノードから発信源への距離線
                if source_pos:
                    self.ax.plot(
                        [node.x, source_pos[0]],
                        [node.y, source_pos[1]],
                        color='#00ff88', alpha=0.2, linestyle=':'
                    )

        # 実際の発信源
        if source_pos:
            self.ax.plot(
                source_pos[0], source_pos[1],
                '*', color='#ff4444', markersize=20, label='実際の発信源'
            )
            self.ax.annotate(
                '📍 発信源',
                source_pos,
                color='#ff4444', fontsize=10,
                ha='center', va='bottom'
            )

        # 推定位置
        if estimated_pos and estimated_pos[0] is not None:
            self.ax.plot(
                estimated_pos[0], estimated_pos[1],
                'D', color='#ff66ff', markersize=15, label='TDOA推定位置'
            )
            self.ax.annotate(
                '🎯 推定位置',
                estimated_pos,
                color='#ff66ff', fontsize=10,
                ha='center', va='top'
            )

            # 誤差を示す円
            if source_pos and estimated_pos[2] is not None:
                circle = __import__('matplotlib.patches', fromlist=['Circle']).Circle(
                    (estimated_pos[0], estimated_pos[1]),
                    estimated_pos[2],
                    color='#ff66ff', fill=False, alpha=0.3, linestyle='--'
                )
                self.ax.add_patch(circle)

        self.ax.legend(
            facecolor='#1a1a2e', labelcolor='#00ff88', fontsize=8,
            loc='upper right'
        )
        self.draw()


class TDOASystem(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("📡 PHENIX TDOAシステム")
        self.setGeometry(100, 100, 1300, 850)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        self.base_lat = -33.2833
        self.base_lng = 149.1000
        self.map_file = os.path.expanduser("~/PHENIX/tdoa_map.html")
        self.running = False
        self.source_x = 300
        self.source_y = 200
        self.estimated_pos = None
        self.error_history = []

        # TDOAノード配置（8個）
        self.nodes = [
            TDOANode(1, 50,  50,  self.base_lat - 0.003, self.base_lng - 0.003),
            TDOANode(2, 300, 50,  self.base_lat - 0.003, self.base_lng),
            TDOANode(3, 550, 50,  self.base_lat - 0.003, self.base_lng + 0.003),
            TDOANode(4, 50,  200, self.base_lat,         self.base_lng - 0.003),
            TDOANode(5, 550, 200, self.base_lat,         self.base_lng + 0.003),
            TDOANode(6, 50,  350, self.base_lat + 0.003, self.base_lng - 0.003),
            TDOANode(7, 300, 350, self.base_lat + 0.003, self.base_lng),
            TDOANode(8, 550, 350, self.base_lat + 0.003, self.base_lng + 0.003),
        ]

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # 左パネル
        left_panel = QWidget()
        left_panel.setMaximumWidth(370)
        left_layout = QVBoxLayout(left_panel)

        title = QLabel("📡 PHENIX TDOAシステム")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title)

        subtitle = QLabel("Time Difference of Arrival\nLoRa電波の到達時間差で位置特定")
        subtitle.setStyleSheet("font-size: 11px; color: #666666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(subtitle)

        # コントロール
        ctrl_group = QGroupBox("🎮 コントロール")
        ctrl_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        ctrl_layout = QVBoxLayout()

        self.btn_start = QPushButton("▶️ TDOAスキャン開始")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                color: #00ff88;
                border: 2px solid #00ff88;
                padding: 10px;
                font-size: 13px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #005500; }
        """)
        self.btn_start.clicked.connect(self.toggle_scan)
        ctrl_layout.addWidget(self.btn_start)

        btn_random = QPushButton("🎲 発信源をランダム移動")
        btn_random.setStyleSheet("""
            QPushButton {
                background-color: #333300;
                color: #ffaa00;
                border: 2px solid #ffaa00;
                padding: 8px;
                font-size: 12px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #555500; }
        """)
        btn_random.clicked.connect(self.random_source)
        ctrl_layout.addWidget(btn_random)

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
            QPushButton:hover { background-color: #005555; }
        """)
        btn_map.clicked.connect(self.open_map)
        ctrl_layout.addWidget(btn_map)

        ctrl_group.setLayout(ctrl_layout)
        left_layout.addWidget(ctrl_group)

        # 発信源位置
        source_group = QGroupBox("📍 発信源位置")
        source_group.setStyleSheet(
            "QGroupBox { color: #ff4444; border: 1px solid #ff4444; padding: 5px; }"
        )
        source_layout = QGridLayout()

        source_layout.addWidget(QLabel("X座標:"), 0, 0)
        self.source_x_slider = QSlider(Qt.Orientation.Horizontal)
        self.source_x_slider.setMinimum(50)
        self.source_x_slider.setMaximum(550)
        self.source_x_slider.setValue(300)
        self.source_x_label = QLabel("300 m")
        self.source_x_label.setStyleSheet("color: #ff4444;")
        self.source_x_slider.valueChanged.connect(self.update_source_x)
        source_layout.addWidget(self.source_x_slider, 0, 1)
        source_layout.addWidget(self.source_x_label, 0, 2)

        source_layout.addWidget(QLabel("Y座標:"), 1, 0)
        self.source_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.source_y_slider.setMinimum(50)
        self.source_y_slider.setMaximum(350)
        self.source_y_slider.setValue(200)
        self.source_y_label = QLabel("200 m")
        self.source_y_label.setStyleSheet("color: #ff4444;")
        self.source_y_slider.valueChanged.connect(self.update_source_y)
        source_layout.addWidget(self.source_y_slider, 1, 1)
        source_layout.addWidget(self.source_y_label, 1, 2)

        source_group.setLayout(source_layout)
        left_layout.addWidget(source_group)

        # 結果表示
        result_group = QGroupBox("🎯 TDOA計算結果")
        result_group.setStyleSheet(
            "QGroupBox { color: #ff66ff; border: 1px solid #ff66ff; padding: 5px; }"
        )
        result_layout = QVBoxLayout()

        self.result_actual = QLabel("実際の位置: ---")
        self.result_actual.setStyleSheet("font-size: 12px; color: #ff4444;")
        result_layout.addWidget(self.result_actual)

        self.result_estimated = QLabel("推定位置: ---")
        self.result_estimated.setStyleSheet("font-size: 12px; color: #ff66ff;")
        result_layout.addWidget(self.result_estimated)

        self.result_error = QLabel("誤差: ---")
        self.result_error.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffaa00;")
        result_layout.addWidget(self.result_error)

        self.result_accuracy = QLabel("精度評価: ---")
        self.result_accuracy.setStyleSheet("font-size: 14px; font-weight: bold;")
        result_layout.addWidget(self.result_accuracy)

        self.result_gps = QLabel("GPS座標: ---")
        self.result_gps.setStyleSheet("font-size: 11px; color: #00aaff;")
        result_layout.addWidget(self.result_gps)

        result_group.setLayout(result_layout)
        left_layout.addWidget(result_group)

        # ノード受信時刻
        node_group = QGroupBox("⏱️ ノード受信時刻")
        node_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        node_layout = QVBoxLayout()
        self.node_time_labels = []
        for i in range(8):
            label = QLabel(f"ノード{i+1}: ---")
            label.setStyleSheet("font-size: 10px; color: #444444;")
            node_layout.addWidget(label)
            self.node_time_labels.append(label)
        node_group.setLayout(node_layout)
        left_layout.addWidget(node_group)

        # アラート
        self.alert_label = QLabel("✅ 待機中")
        self.alert_label.setStyleSheet("font-size: 14px; color: #00ff88; font-weight: bold;")
        self.alert_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.alert_label)

        layout.addWidget(left_panel)

        # 右パネル
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.tdoa_graph = TDOAGraph()
        right_layout.addWidget(self.tdoa_graph)

        # 誤差履歴グラフ
        self.error_fig = Figure(figsize=(6, 2), facecolor='#1a1a2e')
        self.error_ax = self.error_fig.add_subplot(111)
        self.error_ax.set_facecolor('#0a0a1a')
        self.error_canvas = FigureCanvas(self.error_fig)
        right_layout.addWidget(self.error_canvas)

        self.log_text = QTextEdit()
        self.log_text.setStyleSheet(
            "background-color: #050510; color: #00ff88; font-family: monospace; font-size: 11px;"
        )
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        right_layout.addWidget(self.log_text)

        layout.addWidget(right_panel)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_tdoa)

        self.update_map()
        self.log("📡 PHENIX TDOAシステム起動！")
        self.log(f"✅ TDOAノード {len(self.nodes)}個 配置完了")
        self.log("Time Difference of Arrival - LoRa電波の到達時間差で位置特定")
        self.log("「TDOAスキャン開始」ボタンでスキャン開始！")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def update_source_x(self, value):
        self.source_x = value
        self.source_x_label.setText(f"{value} m")

    def update_source_y(self, value):
        self.source_y = value
        self.source_y_label.setText(f"{value} m")

    def random_source(self):
        self.source_x = random.randint(100, 500)
        self.source_y = random.randint(80, 320)
        self.source_x_slider.setValue(self.source_x)
        self.source_y_slider.setValue(self.source_y)
        self.log(f"🎲 発信源を移動: ({self.source_x}, {self.source_y})")

    def toggle_scan(self):
        self.running = not self.running
        if self.running:
            self.timer.start(500)
            self.btn_start.setText("⏹️ スキャン停止")
            self.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #440000;
                    color: #ff4444;
                    border: 2px solid #ff4444;
                    padding: 10px;
                    font-size: 13px;
                    border-radius: 5px;
                }
            """)
            self.log("▶️ TDOAスキャン開始！")
        else:
            self.timer.stop()
            self.btn_start.setText("▶️ TDOAスキャン開始")
            self.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #003300;
                    color: #00ff88;
                    border: 2px solid #00ff88;
                    padding: 10px;
                    font-size: 13px;
                    border-radius: 5px;
                }
            """)
            self.log("⏹️ スキャン停止")

    def update_tdoa(self):
        base_time = 1000.0

        # 各ノードが信号を受信
        active_nodes = [n for n in self.nodes if n.active]
        for node in active_nodes:
            node.receive_signal(self.source_x, self.source_y, base_time)

        # ノード受信時刻を表示
        for i, node in enumerate(self.nodes):
            if node.active:
                tdoa = node.receive_time - active_nodes[0].receive_time
                self.node_time_labels[i].setText(
                    f"ノード{i+1}: {node.receive_time:.2f}μs (Δ{tdoa:+.2f})"
                )
                self.node_time_labels[i].setStyleSheet(
                    "font-size: 10px; color: #00ff88;"
                )

        # TDOA計算
        est_x, est_y, error = tdoa_locate(active_nodes, self.source_x, self.source_y)

        if est_x is not None:
            self.estimated_pos = (est_x, est_y, error)

            # GPS座標変換
            est_lat = self.base_lat + (est_y - 200) * 0.000009
            est_lng = self.base_lng + (est_x - 300) * 0.000009
            actual_lat = self.base_lat + (self.source_y - 200) * 0.000009
            actual_lng = self.base_lng + (self.source_x - 300) * 0.000009

            self.result_actual.setText(
                f"実際の位置: ({self.source_x}, {self.source_y})"
            )
            self.result_estimated.setText(
                f"推定位置: ({est_x:.1f}, {est_y:.1f})"
            )
            self.result_error.setText(f"誤差: {error:.1f} m")
            self.result_gps.setText(
                f"推定GPS: {est_lat:.5f}, {est_lng:.5f}"
            )

            if error < 5:
                accuracy = "🟢 超高精度（<5m）"
                color = "#00ff88"
            elif error < 20:
                accuracy = "🟡 高精度（<20m）"
                color = "#ffaa00"
            elif error < 50:
                accuracy = "🟠 中精度（<50m）"
                color = "#ff8800"
            else:
                accuracy = "🔴 低精度（>50m）"
                color = "#ff4444"

            self.result_accuracy.setText(accuracy)
            self.result_accuracy.setStyleSheet(
                f"font-size: 14px; font-weight: bold; color: {color};"
            )
            self.alert_label.setText(f"📡 TDOA計算完了！誤差: {error:.1f}m")
            self.alert_label.setStyleSheet(
                f"font-size: 14px; color: {color}; font-weight: bold;"
            )

            self.error_history.append(error)
            if len(self.error_history) > 50:
                self.error_history.pop(0)

            self.update_error_graph()
            self.tdoa_graph.update_plot(
                active_nodes,
                (self.source_x, self.source_y),
                (est_x, est_y, error)
            )

            if len(self.error_history) % 10 == 1:
                self.log(
                    f"📡 TDOA計算: 推定({est_x:.0f},{est_y:.0f}) "
                    f"誤差:{error:.1f}m → {accuracy}"
                )
                self.update_map()

    def update_error_graph(self):
        self.error_ax.clear()
        self.error_ax.set_facecolor('#0a0a1a')
        self.error_ax.tick_params(colors='#00ff88')
        for spine in self.error_ax.spines.values():
            spine.set_color('#00ff88')
        self.error_ax.set_title('誤差履歴', color='#00ff88', fontsize=9)
        self.error_ax.set_ylabel('誤差 (m)', color='#00ff88', fontsize=8)
        if self.error_history:
            colors = ['#00ff88' if e < 20 else '#ff4444' for e in self.error_history]
            self.error_ax.bar(
                range(len(self.error_history)),
                self.error_history,
                color=colors, alpha=0.7
            )
            avg = sum(self.error_history) / len(self.error_history)
            self.error_ax.axhline(y=avg, color='#ffaa00', linestyle='--',
                                  label=f'平均: {avg:.1f}m')
            self.error_ax.legend(facecolor='#1a1a2e', labelcolor='#00ff88', fontsize=7)
        self.error_canvas.draw()

    def update_map(self):
        m = folium.Map(
            location=[self.base_lat, self.base_lng],
            zoom_start=16,
            tiles='CartoDB positron'
        )

        for node in self.nodes:
            folium.Marker(
                [node.lat, node.lng],
                tooltip=f"📡 ノード{node.id}",
                icon=folium.Icon(color='green', icon='wifi', prefix='fa')
            ).add_to(m)

        actual_lat = self.base_lat + (self.source_y - 200) * 0.000009
        actual_lng = self.base_lng + (self.source_x - 300) * 0.000009
        folium.Marker(
            [actual_lat, actual_lng],
            tooltip="📍 実際の発信源",
            icon=folium.Icon(color='red', icon='star', prefix='fa')
        ).add_to(m)

        if self.estimated_pos and self.estimated_pos[0] is not None:
            est_lat = self.base_lat + (self.estimated_pos[1] - 200) * 0.000009
            est_lng = self.base_lng + (self.estimated_pos[0] - 300) * 0.000009
            folium.Marker(
                [est_lat, est_lng],
                tooltip=f"🎯 TDOA推定位置 (誤差:{self.estimated_pos[2]:.1f}m)",
                icon=folium.Icon(color='purple', icon='crosshairs', prefix='fa')
            ).add_to(m)
            folium.Circle(
                [est_lat, est_lng],
                radius=self.estimated_pos[2],
                color='#ff66ff',
                fill=True,
                fill_opacity=0.1
            ).add_to(m)

        m.save(self.map_file)

    def open_map(self):
        subprocess.Popen(['firefox', self.map_file])
        self.log("🌐 地図をFirefoxで開きました")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TDOASystem()
    window.show()
    sys.exit(app.exec())