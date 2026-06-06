import sys
import cv2
import random
import math
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ThermalSimulator:
    """サーマルカメラシミュレーター"""

    def __init__(self, width=320, height=240):
        self.width = width
        self.height = height
        self.survivors = []
        self.frame_count = 0

    def add_survivor(self, x, y, temp=37.0):
        self.survivors.append({'x': x, 'y': y, 'temp': temp, 'id': len(self.survivors) + 1})

    def generate_frame(self):
        frame = np.zeros((self.height, self.width), dtype=np.float32)

        # 背景ノイズ（環境温度）
        frame += np.random.normal(20, 2, frame.shape).astype(np.float32)

        # 生存者の熱源
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

        self.frame_count += 1
        return frame

    def detect_survivors(self, frame, threshold=35.0):
        detected = []
        hot_pixels = np.where(frame > threshold)

        if len(hot_pixels[0]) > 0:
            from scipy import ndimage
            try:
                binary = (frame > threshold).astype(np.uint8)
                labeled, num_features = ndimage.label(binary)

                for i in range(1, num_features + 1):
                    region = np.where(labeled == i)
                    if len(region[0]) > 10:
                        cy = int(np.mean(region[0]))
                        cx = int(np.mean(region[1]))
                        max_temp = float(np.max(frame[region]))
                        detected.append({
                            'x': cx, 'y': cy,
                            'temp': max_temp,
                            'confidence': min(100, int((max_temp - threshold) * 10))
                        })
            except ImportError:
                for y, x in zip(hot_pixels[0][::20], hot_pixels[1][::20]):
                    detected.append({
                        'x': int(x), 'y': int(y),
                        'temp': float(frame[y, x]),
                        'confidence': 80
                    })

        return detected


class SurvivorDetectionSystem(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌡️ PHENIX 生存者検知システム")
        self.setGeometry(100, 100, 1300, 800)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        self.thermal = ThermalSimulator()
        self.detection_count = 0
        self.total_detected = 0

        # デフォルト生存者を追加
        self.thermal.add_survivor(160, 120, 37.5)
        self.thermal.add_survivor(80, 180, 36.8)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # 左パネル
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(350)

        title = QLabel("🌡️ PHENIX 生存者検知システム")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title)

        # コントロール
        ctrl_group = QGroupBox("🎮 コントロール")
        ctrl_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }")
        ctrl_layout = QVBoxLayout()

        self.btn_start = QPushButton("▶️ 検知開始")
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
        self.btn_start.clicked.connect(self.start_detection)
        ctrl_layout.addWidget(self.btn_start)

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
        self.btn_stop.clicked.connect(self.stop_detection)
        ctrl_layout.addWidget(self.btn_stop)

        btn_add = QPushButton("➕ 生存者追加")
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #003333;
                color: #00ffff;
                border: 2px solid #00ffff;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #005555; }
        """)
        btn_add.clicked.connect(self.add_random_survivor)
        ctrl_layout.addWidget(btn_add)

        btn_clear = QPushButton("🗑️ クリア")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #333300;
                color: #ffaa00;
                border: 2px solid #ffaa00;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #555500; }
        """)
        btn_clear.clicked.connect(self.clear_survivors)
        ctrl_layout.addWidget(btn_clear)

        ctrl_group.setLayout(ctrl_layout)
        left_layout.addWidget(ctrl_group)

        # 検知閾値スライダー
        threshold_group = QGroupBox("🌡️ 検知閾値")
        threshold_group.setStyleSheet("QGroupBox { color: #ff6666; border: 1px solid #ff6666; padding: 5px; }")
        threshold_layout = QVBoxLayout()

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(30)
        self.threshold_slider.setMaximum(40)
        self.threshold_slider.setValue(35)
        self.threshold_slider.setStyleSheet("QSlider::handle { background-color: #ff6666; }")
        threshold_layout.addWidget(self.threshold_slider)

        self.threshold_label = QLabel("閾値: 35.0 ℃")
        self.threshold_label.setStyleSheet("color: #ff6666; font-size: 14px;")
        threshold_layout.addWidget(self.threshold_label)
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_label.setText(f"閾値: {v}.0 ℃")
        )

        threshold_group.setLayout(threshold_layout)
        left_layout.addWidget(threshold_group)

        # 検知結果
        result_group = QGroupBox("👤 検知結果")
        result_group.setStyleSheet("QGroupBox { color: #ff4444; border: 1px solid #ff4444; padding: 5px; }")
        result_layout = QVBoxLayout()

        self.result_count = QLabel("検知数: 0人")
        self.result_count.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff4444;")
        result_layout.addWidget(self.result_count)

        self.result_total = QLabel("累計検知: 0回")
        self.result_total.setStyleSheet("font-size: 14px; color: #ffaa00;")
        result_layout.addWidget(self.result_total)

        self.result_alert = QLabel("✅ 待機中")
        self.result_alert.setStyleSheet("font-size: 14px; color: #00ff88;")
        result_layout.addWidget(self.result_alert)

        result_group.setLayout(result_layout)
        left_layout.addWidget(result_group)

        # GPS座標表示
        gps_group = QGroupBox("📍 検知座標")
        gps_group.setStyleSheet("QGroupBox { color: #00aaff; border: 1px solid #00aaff; padding: 5px; }")
        gps_layout = QVBoxLayout()

        self.gps_labels = []
        for i in range(3):
            label = QLabel(f"生存者{i+1}: ---")
            label.setStyleSheet("font-size: 12px; color: #00aaff;")
            gps_layout.addWidget(label)
            self.gps_labels.append(label)

        gps_group.setLayout(gps_layout)
        left_layout.addWidget(gps_group)

        layout.addWidget(left_panel)

        # 右パネル：サーマル画像
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # サーマル画像表示
        thermal_group = QGroupBox("🌡️ サーマルカメラ映像")
        thermal_group.setStyleSheet("QGroupBox { color: #ff6666; border: 1px solid #ff6666; padding: 5px; }")
        thermal_layout = QVBoxLayout()

        self.thermal_label = QLabel()
        self.thermal_label.setFixedSize(640, 480)
        self.thermal_label.setStyleSheet("background-color: #000000; border: 1px solid #333333;")
        self.thermal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thermal_layout.addWidget(self.thermal_label)

        thermal_group.setLayout(thermal_layout)
        right_layout.addWidget(thermal_group)

        # ログ
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("background-color: #050510; color: #00ff88; font-family: monospace; font-size: 11px;")
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        right_layout.addWidget(self.log_text)

        layout.addWidget(right_panel)

        # タイマー
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_detection)

        self.log("🌡️ PHENIX 生存者検知システム起動！")
        self.log(f"✅ 初期生存者: {len(self.thermal.survivors)}人配置済み")
        self.log("「検知開始」ボタンでサーマル検知を開始します")

        self.update_thermal_display()

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def start_detection(self):
        self.timer.start(200)
        self.btn_start.setText("▶️ 検知中...")
        self.log("▶️ サーマル検知開始！")

    def stop_detection(self):
        self.timer.stop()
        self.btn_start.setText("▶️ 検知開始")
        self.log("⏹️ 検知停止")

    def add_random_survivor(self):
        x = random.randint(30, 290)
        y = random.randint(30, 210)
        temp = random.uniform(36.5, 38.5)
        self.thermal.add_survivor(x, y, temp)
        self.log(f"➕ 生存者{len(self.thermal.survivors)}追加（体温: {temp:.1f}℃）")

    def clear_survivors(self):
        self.thermal.survivors = []
        self.log("🗑️ 生存者データをクリア")
        self.update_thermal_display()

    def update_thermal_display(self):
        frame = self.thermal.generate_frame()

        # カラーマップ適用
        frame_norm = cv2.normalize(frame, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        frame_color = cv2.applyColorMap(frame_norm, cv2.COLORMAP_INFERNO)

        # 検知した生存者にマーカーを描画
        threshold = self.threshold_slider.value()
        detected = self.thermal.detect_survivors(frame, threshold)

        for det in detected:
            x, y = det['x'], det['y']
            # スケール調整（320x240 → 640x480）
            sx, sy = x * 2, y * 2
            cv2.circle(frame_color, (sx, sy), 20, (0, 255, 0), 2)
            cv2.putText(frame_color, f"{det['temp']:.1f}C {det['confidence']}%",
                       (sx - 30, sy - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # スケールアップ
        frame_large = cv2.resize(frame_color, (640, 480))

        # PyQtで表示
        h, w, c = frame_large.shape
        bytes_per_line = c * w
        qt_image = QImage(frame_large.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        qt_image = qt_image.rgbSwapped()
        pixmap = QPixmap.fromImage(qt_image)
        self.thermal_label.setPixmap(pixmap)

        return detected

    def update_detection(self):
        detected = self.update_thermal_display()
        threshold = self.threshold_slider.value()

        self.result_count.setText(f"検知数: {len(detected)}人")

        if detected:
            self.total_detected += 1
            self.result_total.setText(f"累計検知: {self.total_detected}回")
            self.result_alert.setText(f"⚠️ 生存者{len(detected)}人検知！")
            self.result_alert.setStyleSheet("font-size: 14px; color: #ff4444; font-weight: bold;")

            for i, det in enumerate(detected[:3]):
                # ピクセル座標をGPS座標に変換（簡略）
                lat = -33.2833 + (det['y'] - 120) * 0.00001
                lng = 149.1000 + (det['x'] - 160) * 0.00001
                self.gps_labels[i].setText(
                    f"生存者{i+1}: {lat:.4f}, {lng:.4f} ({det['temp']:.1f}℃)"
                )

            if self.total_detected % 10 == 1:
                self.log(f"⚠️ 生存者{len(detected)}人検知！体温: {detected[0]['temp']:.1f}℃")
        else:
            self.result_alert.setText("✅ 検知なし")
            self.result_alert.setStyleSheet("font-size: 14px; color: #00ff88;")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SurvivorDetectionSystem()
    window.show()
    sys.exit(app.exec())