import sys
import math
import random
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import numpy as np


def gps_to_xyz(lat, lng, alt=0):
    """GPS座標をXYZ座標に変換（メートル）"""
    R = 6371000
    x = R * math.cos(math.radians(lat)) * math.cos(math.radians(lng))
    y = R * math.cos(math.radians(lat)) * math.sin(math.radians(lng))
    z = R * math.sin(math.radians(lat)) + alt
    return x, y, z


def calculate_triangulation(pos1, pos2, pos3, angle1, angle2, angle3):
    """
    3点の位置と各点からの角度で三角測量
    pos: (lat, lng, alt) GPS座標
    angle: (azimuth, elevation) 方位角と仰角（度）
    """
    results = []

    for i, (pos, angle) in enumerate(zip([pos1, pos2, pos3], [angle1, angle2, angle3])):
        lat, lng, alt = pos
        azimuth, elevation = angle

        az_rad = math.radians(azimuth)
        el_rad = math.radians(elevation)

        dx = math.sin(az_rad) * math.cos(el_rad)
        dy = math.cos(az_rad) * math.cos(el_rad)
        dz = math.sin(el_rad)

        results.append({
            'pos': pos,
            'direction': (dx, dy, dz),
            'azimuth': azimuth,
            'elevation': elevation
        })

    # 最小二乗法で交点を求める
    A = []
    b = []

    for r in results:
        lat, lng, alt = r['pos']
        dx, dy, dz = r['direction']

        x0 = (lng - 149.1) * 111320 * math.cos(math.radians(lat))
        y0 = (lat - (-33.28)) * 110540
        z0 = alt

        A.append([1 - dx*dx, -dx*dy, -dx*dz])
        A.append([-dx*dy, 1 - dy*dy, -dy*dz])
        b.append(x0 - dx*(dx*x0 + dy*y0 + dz*z0))
        b.append(y0 - dy*(dx*x0 + dy*y0 + dz*z0))

    try:
        A = np.array(A)
        b = np.array(b)
        result = np.linalg.lstsq(A, b, rcond=None)[0]
        x, y, z = result[0], result[1], result[2] if len(result) > 2 else 0

        # XYZ座標からGPSに変換（簡略版）
        target_lat = -33.28 + y / 110540
        target_lng = 149.1 + x / (111320 * math.cos(math.radians(-33.28)))
        target_alt = z

        return target_lat, target_lng, target_alt, True
    except:
        return 0, 0, 0, False


class TriangulationGraph(FigureCanvas):

    def __init__(self):
        self.fig = Figure(figsize=(8, 6), facecolor='#1a1a2e')
        super().__init__(self.fig)

    def plot_3d(self, sensors, target, estimated):
        self.fig.clear()
        ax = self.fig.add_subplot(111, projection='3d')
        ax.set_facecolor('#0a0a1a')
        self.fig.patch.set_facecolor('#1a1a2e')

        colors = ['#00ff88', '#00aaff', '#ffaa00']
        labels = ['VTOL①', 'VTOL②', '母艦']

        for i, (sensor, color, label) in enumerate(zip(sensors, colors, labels)):
            lat, lng, alt = sensor['pos']
            x = (lng - 149.1) * 111320 * math.cos(math.radians(lat))
            y = (lat - (-33.28)) * 110540
            z = alt
            ax.scatter([x], [y], [z], c=color, s=100, label=label, zorder=5)
            ax.text(x, y, z, f' {label}', color=color, fontsize=8)

            # センサーから推定ターゲットへの線
            if estimated:
                ex = (estimated[1] - 149.1) * 111320 * math.cos(math.radians(-33.28))
                ey = (estimated[0] - (-33.28)) * 110540
                ez = estimated[2]
                ax.plot([x, ex], [y, ey], [z, ez], color=color, alpha=0.3, linestyle='--')

        # 実際のターゲット
        tx = (target[1] - 149.1) * 111320 * math.cos(math.radians(target[0]))
        ty = (target[0] - (-33.28)) * 110540
        tz = target[2]
        ax.scatter([tx], [ty], [tz], c='#ff4444', s=200, marker='*', label='実際の位置', zorder=6)

        # 推定ターゲット
        if estimated:
            ex = (estimated[1] - 149.1) * 111320 * math.cos(math.radians(estimated[0]))
            ey = (estimated[0] - (-33.28)) * 110540
            ez = estimated[2]
            ax.scatter([ex], [ey], [ez], c='#ff66ff', s=200, marker='^', label='推定位置', zorder=6)

        ax.set_xlabel('X (m)', color='#00ff88')
        ax.set_ylabel('Y (m)', color='#00ff88')
        ax.set_zlabel('Z (m)', color='#00ff88')
        ax.set_title('PHENIX 三角測量 3D可視化', color='#00ff88', fontsize=12)
        ax.tick_params(colors='#666666')
        ax.legend(facecolor='#1a1a2e', labelcolor='#00ff88', fontsize=8)
        self.draw()


class TriangulationSystem(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("📐 PHENIX 三角測量システム")
        self.setGeometry(100, 100, 1200, 900)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        # デフォルト座標（オレンジ・オーストラリア）
        self.base_lat = -33.2833
        self.base_lng = 149.1000

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # 左パネル：入力
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(400)

        title = QLabel("📐 PHENIX 三角測量システム")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title)

        # センサー入力
        for i, (name, color, default_alt) in enumerate([
            ("VTOL①", "#00ff88", 30),
            ("VTOL②", "#00aaff", 35),
            ("母艦", "#ffaa00", 2)
        ]):
            group = QGroupBox(f"📍 {name}")
            group.setStyleSheet(f"QGroupBox {{ color: {color}; border: 1px solid {color}; padding: 5px; }}")
            group_layout = QGridLayout()

            group_layout.addWidget(QLabel("緯度:"), 0, 0)
            lat_input = QLineEdit(f"{self.base_lat + (i-1)*0.003:.4f}")
            lat_input.setStyleSheet("background-color: #0a0a1a; color: #00ff88; border: 1px solid #333333;")
            group_layout.addWidget(lat_input, 0, 1)

            group_layout.addWidget(QLabel("経度:"), 1, 0)
            lng_input = QLineEdit(f"{self.base_lng + (i-1)*0.002:.4f}")
            lng_input.setStyleSheet("background-color: #0a0a1a; color: #00ff88; border: 1px solid #333333;")
            group_layout.addWidget(lng_input, 1, 1)

            group_layout.addWidget(QLabel("高度(m):"), 2, 0)
            alt_input = QLineEdit(str(default_alt))
            alt_input.setStyleSheet("background-color: #0a0a1a; color: #00ff88; border: 1px solid #333333;")
            group_layout.addWidget(alt_input, 2, 1)

            group_layout.addWidget(QLabel("方位角(°):"), 3, 0)
            az_input = QLineEdit(f"{random.randint(0, 360)}")
            az_input.setStyleSheet("background-color: #0a0a1a; color: #00ff88; border: 1px solid #333333;")
            group_layout.addWidget(az_input, 3, 1)

            group_layout.addWidget(QLabel("仰角(°):"), 4, 0)
            el_input = QLineEdit(f"{random.randint(-30, -10)}")
            el_input.setStyleSheet("background-color: #0a0a1a; color: #00ff88; border: 1px solid #333333;")
            group_layout.addWidget(el_input, 4, 1)

            group.setLayout(group_layout)
            left_layout.addWidget(group)

            setattr(self, f'lat{i}', lat_input)
            setattr(self, f'lng{i}', lng_input)
            setattr(self, f'alt{i}', alt_input)
            setattr(self, f'az{i}', az_input)
            setattr(self, f'el{i}', el_input)

        # 実際のターゲット
        target_group = QGroupBox("🎯 実際のターゲット（検証用）")
        target_group.setStyleSheet("QGroupBox { color: #ff4444; border: 1px solid #ff4444; padding: 5px; }")
        target_layout = QGridLayout()

        target_layout.addWidget(QLabel("緯度:"), 0, 0)
        self.target_lat = QLineEdit(f"{self.base_lat - 0.002:.4f}")
        self.target_lat.setStyleSheet("background-color: #0a0a1a; color: #ff4444; border: 1px solid #333333;")
        target_layout.addWidget(self.target_lat, 0, 1)

        target_layout.addWidget(QLabel("経度:"), 1, 0)
        self.target_lng = QLineEdit(f"{self.base_lng + 0.001:.4f}")
        self.target_lng.setStyleSheet("background-color: #0a0a1a; color: #ff4444; border: 1px solid #333333;")
        target_layout.addWidget(self.target_lng, 1, 1)

        target_layout.addWidget(QLabel("高度(m):"), 2, 0)
        self.target_alt = QLineEdit("0")
        self.target_alt.setStyleSheet("background-color: #0a0a1a; color: #ff4444; border: 1px solid #333333;")
        target_layout.addWidget(self.target_alt, 2, 1)

        target_group.setLayout(target_layout)
        left_layout.addWidget(target_group)

        # ボタン
        btn_layout = QHBoxLayout()

        btn_calc = QPushButton("📐 三角測量実行")
        btn_calc.setStyleSheet("""
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
        btn_calc.clicked.connect(self.calculate)
        btn_layout.addWidget(btn_calc)

        btn_random = QPushButton("🎲 ランダムデータ")
        btn_random.setStyleSheet("""
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
        btn_random.clicked.connect(self.random_data)
        btn_layout.addWidget(btn_random)

        left_layout.addLayout(btn_layout)

        # 結果表示
        result_group = QGroupBox("📊 計算結果")
        result_group.setStyleSheet("QGroupBox { color: #ff66ff; border: 1px solid #ff66ff; padding: 5px; }")
        result_layout = QVBoxLayout()

        self.result_lat = QLabel("推定緯度: ---")
        self.result_lat.setStyleSheet("font-size: 13px; color: #ff66ff;")
        result_layout.addWidget(self.result_lat)

        self.result_lng = QLabel("推定経度: ---")
        self.result_lng.setStyleSheet("font-size: 13px; color: #ff66ff;")
        result_layout.addWidget(self.result_lng)

        self.result_alt = QLabel("推定高度: ---")
        self.result_alt.setStyleSheet("font-size: 13px; color: #ff66ff;")
        result_layout.addWidget(self.result_alt)

        self.result_error = QLabel("誤差: ---")
        self.result_error.setStyleSheet("font-size: 14px; color: #ffaa00; font-weight: bold;")
        result_layout.addWidget(self.result_error)

        self.result_accuracy = QLabel("精度評価: ---")
        self.result_accuracy.setStyleSheet("font-size: 14px; font-weight: bold;")
        result_layout.addWidget(self.result_accuracy)

        result_group.setLayout(result_layout)
        left_layout.addWidget(result_group)

        layout.addWidget(left_panel)

        # 右パネル：3Dグラフ
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.graph = TriangulationGraph()
        right_layout.addWidget(self.graph)

        # ログ
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("background-color: #050510; color: #00ff88; font-family: monospace; font-size: 11px;")
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        right_layout.addWidget(self.log_text)

        layout.addWidget(right_panel)

        self.log("📐 PHENIX 三角測量システム起動！")
        self.log("センサー位置と角度を入力して「三角測量実行」を押してください")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def get_sensor_data(self):
        sensors = []
        angles = []
        for i in range(3):
            try:
                lat = float(getattr(self, f'lat{i}').text())
                lng = float(getattr(self, f'lng{i}').text())
                alt = float(getattr(self, f'alt{i}').text())
                az = float(getattr(self, f'az{i}').text())
                el = float(getattr(self, f'el{i}').text())
                sensors.append({'pos': (lat, lng, alt)})
                angles.append((az, el))
            except:
                return None, None
        return sensors, angles

    def calculate(self):
        sensors, angles = self.get_sensor_data()
        if not sensors:
            self.log("⚠️ 入力値にエラーがあります")
            return

        try:
            target_lat = float(self.target_lat.text())
            target_lng = float(self.target_lng.text())
            target_alt = float(self.target_alt.text())
        except:
            self.log("⚠️ ターゲット座標にエラーがあります")
            return

        self.log("📐 三角測量計算開始...")

        est_lat, est_lng, est_alt, success = calculate_triangulation(
            sensors[0]['pos'], sensors[1]['pos'], sensors[2]['pos'],
            angles[0], angles[1], angles[2]
        )

        if success:
            # 誤差計算（メートル）
            dlat = (est_lat - target_lat) * 110540
            dlng = (est_lng - target_lng) * 111320 * math.cos(math.radians(target_lat))
            dalt = est_alt - target_alt
            error = math.sqrt(dlat**2 + dlng**2 + dalt**2)

            self.result_lat.setText(f"推定緯度: {est_lat:.6f}")
            self.result_lng.setText(f"推定経度: {est_lng:.6f}")
            self.result_alt.setText(f"推定高度: {est_alt:.1f} m")
            self.result_error.setText(f"誤差: {error:.2f} m")

            if error < 1:
                accuracy = "🟢 超高精度（<1m）"
                color = "#00ff88"
            elif error < 5:
                accuracy = "🟡 高精度（<5m）"
                color = "#ffaa00"
            elif error < 10:
                accuracy = "🟠 中精度（<10m）"
                color = "#ff8800"
            else:
                accuracy = "🔴 低精度（>10m）"
                color = "#ff4444"

            self.result_accuracy.setText(accuracy)
            self.result_accuracy.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")

            self.log(f"✅ 計算完了！")
            self.log(f"📍 推定位置: {est_lat:.6f}, {est_lng:.6f}")
            self.log(f"📏 誤差: {error:.2f}m → {accuracy}")

            self.graph.plot_3d(
                sensors,
                (target_lat, target_lng, target_alt),
                (est_lat, est_lng, est_alt)
            )
        else:
            self.log("❌ 計算失敗。入力値を確認してください")

    def random_data(self):
        """ランダムデモデータを生成"""
        target_lat = self.base_lat + random.uniform(-0.005, 0.005)
        target_lng = self.base_lng + random.uniform(-0.005, 0.005)

        self.target_lat.setText(f"{target_lat:.4f}")
        self.target_lng.setText(f"{target_lng:.4f}")
        self.target_alt.setText("0")

        positions = [
            (self.base_lat + 0.003, self.base_lng - 0.002, 30),
            (self.base_lat - 0.002, self.base_lng + 0.003, 35),
            (self.base_lat + 0.001, self.base_lng + 0.004, 2),
        ]

        for i, (lat, lng, alt) in enumerate(positions):
            dlat = target_lat - lat
            dlng = target_lng - lng
            dalt = -alt

            azimuth = math.degrees(math.atan2(dlng, dlat)) % 360
            distance_h = math.sqrt(dlat**2 * 110540**2 + dlng**2 * 111320**2)
            elevation = math.degrees(math.atan2(dalt, distance_h))

            getattr(self, f'lat{i}').setText(f"{lat:.4f}")
            getattr(self, f'lng{i}').setText(f"{lng:.4f}")
            getattr(self, f'alt{i}').setText(str(alt))
            getattr(self, f'az{i}').setText(f"{azimuth:.1f}")
            getattr(self, f'el{i}').setText(f"{elevation:.1f}")

        self.log("🎲 ランダムデータ生成完了！「三角測量実行」を押してください")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TriangulationSystem()
    window.show()
    sys.exit(app.exec())