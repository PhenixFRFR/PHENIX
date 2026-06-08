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
from scipy.spatial import Voronoi
from scipy.optimize import minimize


class MissionArea:
    """ミッションエリア（被災地）"""
    def __init__(self, width=600, height=400):
        self.width = width
        self.height = height
        self.obstacles = []
        self.survivors = []
        self.no_fly_zones = []

    def add_obstacle(self, x, y, radius):
        self.obstacles.append({'x': x, 'y': y, 'radius': radius})

    def add_survivor(self, x, y):
        self.survivors.append({'x': x, 'y': y})

    def add_no_fly_zone(self, x, y, radius):
        self.no_fly_zones.append({'x': x, 'y': y, 'radius': radius})

    def is_valid_position(self, x, y):
        if x < 0 or x > self.width or y < 0 or y > self.height:
            return False
        for obs in self.obstacles:
            if math.sqrt((x - obs['x'])**2 + (y - obs['y'])**2) < obs['radius']:
                return False
        return True


class AIPlanner:
    """AIミッションプランナー"""

    def __init__(self, area, num_nodes=24):
        self.area = area
        self.num_nodes = num_nodes
        self.node_range = 80  # ノードの通信範囲（ピクセル）
        self.mother_nodes = 8
        self.vtol1_nodes = 8
        self.vtol2_nodes = 8

    def calculate_coverage(self, positions):
        """カバレッジを計算"""
        grid_size = 20
        covered = 0
        total = 0
        for gx in range(0, self.area.width, grid_size):
            for gy in range(0, self.area.height, grid_size):
                if self.area.is_valid_position(gx, gy):
                    total += 1
                    for pos in positions:
                        dist = math.sqrt((gx - pos[0])**2 + (gy - pos[1])**2)
                        if dist <= self.node_range:
                            covered += 1
                            break
        return covered / total if total > 0 else 0

    def optimize_node_positions(self, progress_callback=None):
        """遺伝的アルゴリズムで最適ノード配置を計算"""
        best_positions = []
        best_coverage = 0

        # 生存者周辺を優先的にカバー
        survivor_positions = [(s['x'], s['y']) for s in self.area.survivors]

        for attempt in range(50):
            if progress_callback:
                progress_callback(attempt * 2)

            positions = []
            for i in range(self.num_nodes):
                # 生存者がいる場合はその周辺を優先
                if survivor_positions and random.random() < 0.4:
                    base = random.choice(survivor_positions)
                    x = base[0] + random.uniform(-100, 100)
                    y = base[1] + random.uniform(-100, 100)
                else:
                    x = random.uniform(20, self.area.width - 20)
                    y = random.uniform(20, self.area.height - 20)

                x = max(10, min(self.area.width - 10, x))
                y = max(10, min(self.area.height - 10, y))

                if self.area.is_valid_position(x, y):
                    positions.append((x, y))
                else:
                    positions.append((
                        random.uniform(20, self.area.width - 20),
                        random.uniform(20, self.area.height - 20)
                    ))

            coverage = self.calculate_coverage(positions)

            # 生存者カバレッジボーナス
            survivor_bonus = 0
            for sv in self.area.survivors:
                for pos in positions:
                    dist = math.sqrt((sv['x'] - pos[0])**2 + (sv['y'] - pos[1])**2)
                    if dist <= self.node_range:
                        survivor_bonus += 0.1
                        break

            total_score = coverage + survivor_bonus

            if total_score > best_coverage:
                best_coverage = total_score
                best_positions = positions.copy()

        return best_positions, best_coverage

    def calculate_mother_route(self, node_positions):
        """母艦の最適ルートを計算（TSP近似）"""
        ground_nodes = node_positions[:self.mother_nodes]

        if not ground_nodes:
            return []

        # 最近傍法でルートを計算
        start = (self.area.width // 4, self.area.height // 2)
        route = [start]
        remaining = list(ground_nodes)

        current = start
        while remaining:
            nearest = min(remaining,
                         key=lambda p: math.sqrt((p[0]-current[0])**2 + (p[1]-current[1])**2))
            route.append(nearest)
            remaining.remove(nearest)
            current = nearest

        return route

    def calculate_vtol_routes(self, node_positions):
        """VTOLの最適ルートを計算"""
        vtol1_nodes = node_positions[self.mother_nodes:self.mother_nodes + self.vtol1_nodes]
        vtol2_nodes = node_positions[self.mother_nodes + self.vtol1_nodes:]

        def calc_route(nodes, start_offset):
            if not nodes:
                return []
            start = (self.area.width // 2 + start_offset, self.area.height // 2)
            route = [start]
            remaining = list(nodes)
            current = start
            while remaining:
                nearest = min(remaining,
                             key=lambda p: math.sqrt((p[0]-current[0])**2 + (p[1]-current[1])**2))
                route.append(nearest)
                remaining.remove(nearest)
                current = nearest
            return route

        return calc_route(vtol1_nodes, -50), calc_route(vtol2_nodes, 50)

    def estimate_mission_time(self, mother_route, vtol1_route, vtol2_route):
        """ミッション時間を推定"""
        def route_distance(route):
            total = 0
            for i in range(1, len(route)):
                dx = route[i][0] - route[i-1][0]
                dy = route[i][1] - route[i-1][1]
                total += math.sqrt(dx**2 + dy**2)
            return total

        mother_dist = route_distance(mother_route) * 0.1  # スケール係数
        vtol1_dist = route_distance(vtol1_route) * 0.05
        vtol2_dist = route_distance(vtol2_route) * 0.05

        mother_time = mother_dist / 5  # 5m/s
        vtol_time = max(vtol1_dist, vtol2_dist) / 10  # 10m/s

        return max(mother_time, vtol_time)


class MissionGraph(FigureCanvas):

    def __init__(self):
        self.fig = Figure(figsize=(7, 5), facecolor='#1a1a2e')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#0a0a1a')
        super().__init__(self.fig)

    def update_plot(self, area, node_positions, mother_route=None,
                    vtol1_route=None, vtol2_route=None, node_range=80):
        self.ax.clear()
        self.ax.set_facecolor('#0a0a1a')
        self.ax.tick_params(colors='#00ff88')
        for spine in self.ax.spines.values():
            spine.set_color('#00ff88')
        self.ax.set_xlim(0, area.width)
        self.ax.set_ylim(0, area.height)
        self.ax.set_title('AIミッションプランナー', color='#00ff88', fontsize=11)
        self.ax.grid(color='#222222', linestyle='--', alpha=0.3)

        # 障害物
        for obs in area.obstacles:
            circle = __import__('matplotlib.patches', fromlist=['Circle']).Circle(
                (obs['x'], obs['y']), obs['radius'],
                color='#ff4444', fill=True, alpha=0.3
            )
            self.ax.add_patch(circle)
            self.ax.plot(obs['x'], obs['y'], 'x', color='#ff4444', markersize=10)

        # ノードカバレッジ
        if node_positions:
            mother_nodes = node_positions[:8]
            vtol1_nodes = node_positions[8:16]
            vtol2_nodes = node_positions[16:]

            for pos in mother_nodes:
                circle = __import__('matplotlib.patches', fromlist=['Circle']).Circle(
                    pos, node_range, color='#00ff88', fill=True, alpha=0.08
                )
                self.ax.add_patch(circle)
                self.ax.plot(pos[0], pos[1], '^', color='#00ff88', markersize=8)

            for pos in vtol1_nodes:
                circle = __import__('matplotlib.patches', fromlist=['Circle']).Circle(
                    pos, node_range, color='#00aaff', fill=True, alpha=0.08
                )
                self.ax.add_patch(circle)
                self.ax.plot(pos[0], pos[1], 's', color='#00aaff', markersize=8)

            for pos in vtol2_nodes:
                circle = __import__('matplotlib.patches', fromlist=['Circle']).Circle(
                    pos, node_range, color='#ffaa00', fill=True, alpha=0.08
                )
                self.ax.add_patch(circle)
                self.ax.plot(pos[0], pos[1], 'D', color='#ffaa00', markersize=8)

        # 母艦ルート
        if mother_route and len(mother_route) > 1:
            xs = [p[0] for p in mother_route]
            ys = [p[1] for p in mother_route]
            self.ax.plot(xs, ys, '-', color='#00ff88', alpha=0.6, linewidth=2, label='母艦ルート')
            self.ax.plot(xs[0], ys[0], 'o', color='#00ff88', markersize=15)

        # VTOLルート
        if vtol1_route and len(vtol1_route) > 1:
            xs = [p[0] for p in vtol1_route]
            ys = [p[1] for p in vtol1_route]
            self.ax.plot(xs, ys, '--', color='#00aaff', alpha=0.6, linewidth=2, label='VTOL①')

        if vtol2_route and len(vtol2_route) > 1:
            xs = [p[0] for p in vtol2_route]
            ys = [p[1] for p in vtol2_route]
            self.ax.plot(xs, ys, '--', color='#ffaa00', alpha=0.6, linewidth=2, label='VTOL②')

        # 生存者
        for i, sv in enumerate(area.survivors):
            self.ax.plot(sv['x'], sv['y'], '*', color='#ff4444', markersize=15)
            self.ax.annotate(f'生存者{i+1}', (sv['x'], sv['y']),
                           color='#ff4444', fontsize=8)

        self.ax.legend(facecolor='#1a1a2e', labelcolor='#00ff88', fontsize=8)
        self.draw()


class MissionPlannerSystem(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🤖 PHENIX AIミッションプランナー")
        self.setGeometry(50, 50, 1400, 900)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        self.base_lat = -33.2833
        self.base_lng = 149.1000
        self.map_file = os.path.expanduser("~/PHENIX/mission_map.html")
        self.area = MissionArea()
        self.planner = AIPlanner(self.area)
        self.node_positions = []
        self.mother_route = []
        self.vtol1_route = []
        self.vtol2_route = []
        self.coverage = 0

        # デフォルト障害物と生存者
        self.area.add_obstacle(200, 150, 40)
        self.area.add_obstacle(400, 280, 50)
        self.area.add_survivor(150, 200)
        self.area.add_survivor(450, 150)
        self.area.add_survivor(300, 320)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # 左パネル
        left_panel = QWidget()
        left_panel.setMaximumWidth(380)
        left_layout = QVBoxLayout(left_panel)

        title = QLabel("🤖 PHENIX AIミッションプランナー")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title)

        subtitle = QLabel("AI最適化でノード配置・ルートを自動計算")
        subtitle.setStyleSheet("font-size: 11px; color: #666666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(subtitle)

        # ミッション設定
        mission_group = QGroupBox("⚙️ ミッション設定")
        mission_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        mission_layout = QGridLayout()

        mission_layout.addWidget(QLabel("ノード数:"), 0, 0)
        self.node_slider = QSlider(Qt.Orientation.Horizontal)
        self.node_slider.setMinimum(8)
        self.node_slider.setMaximum(24)
        self.node_slider.setValue(24)
        self.node_label = QLabel("24個")
        self.node_label.setStyleSheet("color: #00aaff;")
        self.node_slider.valueChanged.connect(
            lambda v: self.node_label.setText(f"{v}個")
        )
        mission_layout.addWidget(self.node_slider, 0, 1)
        mission_layout.addWidget(self.node_label, 0, 2)

        mission_layout.addWidget(QLabel("通信範囲:"), 1, 0)
        self.range_slider = QSlider(Qt.Orientation.Horizontal)
        self.range_slider.setMinimum(50)
        self.range_slider.setMaximum(150)
        self.range_slider.setValue(80)
        self.range_label = QLabel("80px")
        self.range_label.setStyleSheet("color: #ffaa00;")
        self.range_slider.valueChanged.connect(
            lambda v: self.range_label.setText(f"{v}px")
        )
        mission_layout.addWidget(self.range_slider, 1, 1)
        mission_layout.addWidget(self.range_label, 1, 2)

        mission_group.setLayout(mission_layout)
        left_layout.addWidget(mission_group)

        # コントロール
        ctrl_group = QGroupBox("🎮 コントロール")
        ctrl_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        ctrl_layout = QVBoxLayout()

        self.btn_plan = QPushButton("🤖 AIミッション計画実行")
        self.btn_plan.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                color: #00ff88;
                border: 2px solid #00ff88;
                padding: 12px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #005500; }
        """)
        self.btn_plan.clicked.connect(self.run_planning)
        ctrl_layout.addWidget(self.btn_plan)

        btn_add_obs = QPushButton("🚧 障害物を追加")
        btn_add_obs.setStyleSheet("""
            QPushButton {
                background-color: #330000;
                color: #ff4444;
                border: 2px solid #ff4444;
                padding: 8px;
                font-size: 12px;
                border-radius: 5px;
            }
        """)
        btn_add_obs.clicked.connect(self.add_random_obstacle)
        ctrl_layout.addWidget(btn_add_obs)

        btn_add_sv = QPushButton("👤 生存者を追加")
        btn_add_sv.setStyleSheet("""
            QPushButton {
                background-color: #440000;
                color: #ff6666;
                border: 2px solid #ff6666;
                padding: 8px;
                font-size: 12px;
                border-radius: 5px;
            }
        """)
        btn_add_sv.clicked.connect(self.add_random_survivor)
        ctrl_layout.addWidget(btn_add_sv)

        btn_clear = QPushButton("🗑️ リセット")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #333300;
                color: #ffaa00;
                border: 2px solid #ffaa00;
                padding: 8px;
                font-size: 12px;
                border-radius: 5px;
            }
        """)
        btn_clear.clicked.connect(self.reset_mission)
        ctrl_layout.addWidget(btn_clear)

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

        # プログレス
        self.progress = QProgressBar()
        self.progress.setStyleSheet("QProgressBar::chunk { background-color: #00ff88; }")
        self.progress.setValue(0)
        left_layout.addWidget(self.progress)

        # 結果
        result_group = QGroupBox("📊 計画結果")
        result_group.setStyleSheet(
            "QGroupBox { color: #ff66ff; border: 1px solid #ff66ff; padding: 5px; }"
        )
        result_layout = QVBoxLayout()

        self.coverage_label = QLabel("カバレッジ: ---")
        self.coverage_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #00ff88;")
        result_layout.addWidget(self.coverage_label)

        self.nodes_label = QLabel("ノード配置: ---")
        self.nodes_label.setStyleSheet("font-size: 12px; color: #00aaff;")
        result_layout.addWidget(self.nodes_label)

        self.time_label = QLabel("推定ミッション時間: ---")
        self.time_label.setStyleSheet("font-size: 12px; color: #ffaa00;")
        result_layout.addWidget(self.time_label)

        self.survivor_label = QLabel("生存者カバー: ---")
        self.survivor_label.setStyleSheet("font-size: 12px; color: #ff4444;")
        result_layout.addWidget(self.survivor_label)

        self.area_label = QLabel("カバー面積: ---")
        self.area_label.setStyleSheet("font-size: 12px; color: #ff66ff;")
        result_layout.addWidget(self.area_label)

        result_group.setLayout(result_layout)
        left_layout.addWidget(result_group)

        # ノード配置詳細
        detail_group = QGroupBox("📡 ノード配置詳細")
        detail_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        detail_layout = QVBoxLayout()
        self.mother_label = QLabel("母艦ノード（8個）: 未計算")
        self.mother_label.setStyleSheet("font-size: 11px; color: #00ff88;")
        detail_layout.addWidget(self.mother_label)
        self.vtol1_label = QLabel("VTOL①ノード（8個）: 未計算")
        self.vtol1_label.setStyleSheet("font-size: 11px; color: #00aaff;")
        detail_layout.addWidget(self.vtol1_label)
        self.vtol2_label = QLabel("VTOL②ノード（8個）: 未計算")
        self.vtol2_label.setStyleSheet("font-size: 11px; color: #ffaa00;")
        detail_layout.addWidget(self.vtol2_label)
        detail_group.setLayout(detail_layout)
        left_layout.addWidget(detail_group)

        layout.addWidget(left_panel)

        # 右パネル
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.graph = MissionGraph()
        right_layout.addWidget(self.graph)

        self.log_text = QTextEdit()
        self.log_text.setStyleSheet(
            "background-color: #050510; color: #00ff88; font-family: monospace; font-size: 11px;"
        )
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        right_layout.addWidget(self.log_text)

        layout.addWidget(right_panel)

        self.update_graph()
        self.log("🤖 PHENIX AIミッションプランナー起動！")
        self.log(f"✅ ミッションエリア: {self.area.width}×{self.area.height}m")
        self.log(f"✅ 障害物: {len(self.area.obstacles)}個")
        self.log(f"✅ 生存者: {len(self.area.survivors)}人")
        self.log("「AIミッション計画実行」で最適配置を計算します！")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def update_graph(self):
        self.graph.update_plot(
            self.area, self.node_positions,
            self.mother_route, self.vtol1_route, self.vtol2_route,
            self.range_slider.value()
        )

    def run_planning(self):
        self.btn_plan.setText("🤖 計算中...")
        self.btn_plan.setEnabled(False)
        self.progress.setValue(0)
        self.log("🤖 AI最適化開始！")

        num_nodes = self.node_slider.value()
        self.planner.num_nodes = num_nodes
        self.planner.node_range = self.range_slider.value()
        self.planner.mother_nodes = min(8, num_nodes // 3)
        self.planner.vtol1_nodes = min(8, (num_nodes - self.planner.mother_nodes) // 2)
        self.planner.vtol2_nodes = num_nodes - self.planner.mother_nodes - self.planner.vtol1_nodes

        def progress_callback(value):
            self.progress.setValue(value)
            QApplication.processEvents()

        self.node_positions, self.coverage = self.planner.optimize_node_positions(
            progress_callback
        )
        self.progress.setValue(80)
        QApplication.processEvents()

        self.mother_route = self.planner.calculate_mother_route(self.node_positions)
        self.vtol1_route, self.vtol2_route = self.planner.calculate_vtol_routes(
            self.node_positions
        )
        self.progress.setValue(95)
        QApplication.processEvents()

        mission_time = self.planner.estimate_mission_time(
            self.mother_route, self.vtol1_route, self.vtol2_route
        )

        # 生存者カバー率
        covered_survivors = 0
        for sv in self.area.survivors:
            for pos in self.node_positions:
                dist = math.sqrt((sv['x'] - pos[0])**2 + (sv['y'] - pos[1])**2)
                if dist <= self.planner.node_range:
                    covered_survivors += 1
                    break

        # カバー面積（km²換算）
        scale = 0.01  # 1px = 1m として
        area_km2 = self.coverage * self.area.width * self.area.height * scale**2

        self.coverage_label.setText(f"カバレッジ: {self.coverage*100:.1f}%")
        self.nodes_label.setText(f"ノード配置: {len(self.node_positions)}個最適化完了")
        self.time_label.setText(f"推定ミッション時間: {mission_time:.0f}秒（{mission_time/60:.1f}分）")
        self.survivor_label.setText(
            f"生存者カバー: {covered_survivors}/{len(self.area.survivors)}人"
        )
        self.area_label.setText(f"カバー面積: {area_km2:.2f} km²")

        self.mother_label.setText(
            f"母艦ノード（{self.planner.mother_nodes}個）: ルート{len(self.mother_route)}点"
        )
        self.vtol1_label.setText(
            f"VTOL①ノード（{self.planner.vtol1_nodes}個）: ルート{len(self.vtol1_route)}点"
        )
        self.vtol2_label.setText(
            f"VTOL②ノード（{self.planner.vtol2_nodes}個）: ルート{len(self.vtol2_route)}点"
        )

        self.progress.setValue(100)
        self.update_graph()
        self.update_map()

        self.log(f"✅ AI最適化完了！")
        self.log(f"📊 カバレッジ: {self.coverage*100:.1f}%")
        self.log(f"👤 生存者カバー: {covered_survivors}/{len(self.area.survivors)}人")
        self.log(f"⏱️ 推定時間: {mission_time:.0f}秒（{mission_time/60:.1f}分）")
        self.log(f"📡 母艦ルート: {len(self.mother_route)}点")
        self.log(f"🚁 VTOL①ルート: {len(self.vtol1_route)}点")
        self.log(f"🚁 VTOL②ルート: {len(self.vtol2_route)}点")

        self.btn_plan.setText("🤖 AIミッション計画実行")
        self.btn_plan.setEnabled(True)

    def add_random_obstacle(self):
        x = random.randint(50, self.area.width - 50)
        y = random.randint(50, self.area.height - 50)
        r = random.randint(20, 60)
        self.area.add_obstacle(x, y, r)
        self.log(f"🚧 障害物追加: ({x}, {y}) 半径{r}")
        self.update_graph()

    def add_random_survivor(self):
        x = random.randint(30, self.area.width - 30)
        y = random.randint(30, self.area.height - 30)
        self.area.add_survivor(x, y)
        self.log(f"👤 生存者追加: ({x}, {y})")
        self.update_graph()

    def reset_mission(self):
        self.area = MissionArea()
        self.planner = AIPlanner(self.area)
        self.node_positions = []
        self.mother_route = []
        self.vtol1_route = []
        self.vtol2_route = []
        self.coverage = 0
        self.progress.setValue(0)
        self.coverage_label.setText("カバレッジ: ---")
        self.nodes_label.setText("ノード配置: ---")
        self.time_label.setText("推定ミッション時間: ---")
        self.survivor_label.setText("生存者カバー: ---")
        self.area_label.setText("カバー面積: ---")
        self.log("🗑️ ミッションをリセットしました")
        self.update_graph()

    def update_map(self):
        m = folium.Map(
            location=[self.base_lat, self.base_lng],
            zoom_start=14,
            tiles='CartoDB positron'
        )

        scale = 0.000009

        # 母艦スタート
        folium.Marker(
            [self.base_lat, self.base_lng],
            tooltip="🔴 母艦スタート地点",
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(m)

        # ノード
        colors = ['green'] * 8 + ['blue'] * 8 + ['orange'] * 8
        labels = ['母艦'] * 8 + ['VTOL①'] * 8 + ['VTOL②'] * 8

        for i, (pos, color, label) in enumerate(
            zip(self.node_positions, colors, labels)
        ):
            lat = self.base_lat + (pos[1] - 200) * scale
            lng = self.base_lng + (pos[0] - 300) * scale
            folium.Marker(
                [lat, lng],
                tooltip=f"📡 {label}ノード{i+1}",
                icon=folium.Icon(color=color, icon='wifi', prefix='fa')
            ).add_to(m)
            folium.Circle(
                [lat, lng],
                radius=self.planner.node_range * 0.9,
                color='#00ff88' if color == 'green' else '#00aaff' if color == 'blue' else '#ffaa00',
                fill=True, fill_opacity=0.05
            ).add_to(m)

        # 生存者
        for i, sv in enumerate(self.area.survivors):
            lat = self.base_lat + (sv['y'] - 200) * scale
            lng = self.base_lng + (sv['x'] - 300) * scale
            folium.Marker(
                [lat, lng],
                tooltip=f"⚠️ 生存者{i+1}",
                icon=folium.Icon(color='red', icon='user', prefix='fa')
            ).add_to(m)

        # 母艦ルート
        if len(self.mother_route) > 1:
            route_coords = [
                [self.base_lat + (p[1] - 200) * scale,
                 self.base_lng + (p[0] - 300) * scale]
                for p in self.mother_route
            ]
            folium.PolyLine(
                route_coords, color='#00ff88',
                weight=3, opacity=0.7, tooltip="母艦ルート"
            ).add_to(m)

        m.save(self.map_file)

    def open_map(self):
        subprocess.Popen(['firefox', self.map_file])
        self.log("🌐 地図をFirefoxで開きました")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MissionPlannerSystem()
    window.show()
    sys.exit(app.exec())