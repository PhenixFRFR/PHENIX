import sys
import subprocess
import os
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


class PHENIXLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔥 PHENIX Launcher v3.0")
        self.setGeometry(400, 150, 650, 950)
        self.setStyleSheet("background-color: #0a0a1a; color: #00ff88;")
        self.processes = {}

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # ロゴ
        logo = QLabel("🔥 PHENIX")
        logo.setStyleSheet("font-size: 48px; font-weight: bold; color: #00ff88;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        subtitle = QLabel("Autonomous Distributed Antenna System")
        subtitle.setStyleSheet("font-size: 13px; color: #666666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        version = QLabel("v3.0 - 2026 | Phase 7 Complete")
        version.setStyleSheet("font-size: 11px; color: #444444;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #00ff88;")
        layout.addWidget(line)

        # 全部起動ボタン
        self.btn_all = QPushButton("🚀 全システム起動")
        self.btn_all.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                color: #00ff88;
                border: 3px solid #00ff88;
                padding: 15px;
                font-size: 18px;
                font-weight: bold;
                border-radius: 10px;
            }
            QPushButton:hover { background-color: #005500; }
            QPushButton:pressed { background-color: #00ff88; color: #000000; }
        """)
        self.btn_all.clicked.connect(self.launch_all)
        layout.addWidget(self.btn_all)

        # ── コアシステム ──
        core_group = QGroupBox("🔥 コアシステム")
        core_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 2px solid #00ff88;"
            "padding: 10px; font-size: 13px; font-weight: bold; margin-top: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; }"
        )
        core_layout = QVBoxLayout()

        core_apps = [
            ("🖥️ Command Center v3.2", '#00ff88', 'phenix_main.py', 'Command Center'),
            ("🗺️ マップビューア",        '#ffaa00', 'map_viewer.py',   'Map Viewer'),
            ("📊 データ分析ツール",       '#ff66ff', 'data_analyzer.py','Data Analyzer'),
        ]
        for text, color, script, name in core_apps:
            btn = self._make_btn(text, color, script, name)
            core_layout.addWidget(btn)

        core_group.setLayout(core_layout)
        layout.addWidget(core_group)

        # ── ミッション管理 ──
        mission_group = QGroupBox("🗂️ ミッション管理")
        mission_group.setStyleSheet(
            "QGroupBox { color: #00aaff; border: 2px solid #00aaff;"
            "padding: 10px; font-size: 13px; font-weight: bold; margin-top: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; }"
        )
        mission_layout = QVBoxLayout()

        mission_apps = [
            ("🗺️ ミッションプランナー", '#00aaff', 'mission_planner.py', 'Mission Planner'),
            ("📋 ミッションレポート",   '#66ffff', 'mission_report.py',  'Mission Report'),
        ]
        for text, color, script, name in mission_apps:
            btn = self._make_btn(text, color, script, name)
            mission_layout.addWidget(btn)

        mission_group.setLayout(mission_layout)
        layout.addWidget(mission_group)

        # ── 検知・センサー ──
        sensor_group = QGroupBox("📡 検知・センサー")
        sensor_group.setStyleSheet(
            "QGroupBox { color: #ff66ff; border: 2px solid #ff66ff;"
            "padding: 10px; font-size: 13px; font-weight: bold; margin-top: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; }"
        )
        sensor_layout = QVBoxLayout()

        sensor_apps = [
            ("🌡️ 生存者検知",       '#ff4444', 'survivor_detections.py','Survivor Detection'),
            ("📐 三角測量システム", '#00ffff', 'triangulation.py',       'Triangulation'),
            ("📡 レーダー検知",     '#66ff66', 'radar_detection.py',     'Radar Detection'),
            ("📡 TDOAシステム",     '#ff9900', 'tdoa_system.py',         'TDOA'),
        ]
        for text, color, script, name in sensor_apps:
            btn = self._make_btn(text, color, script, name)
            sensor_layout.addWidget(btn)

        sensor_group.setLayout(sensor_layout)
        layout.addWidget(sensor_group)

        # ── 通知・モニタリング ──
        notify_group = QGroupBox("🔔 通知・モニタリング")
        notify_group.setStyleSheet(
            "QGroupBox { color: #ffaa00; border: 2px solid #ffaa00;"
            "padding: 10px; font-size: 13px; font-weight: bold; margin-top: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; }"
        )
        notify_layout = QVBoxLayout()

        notify_apps = [
            ("🔊 音声アラート",       '#ffaa00', 'voice_alert.py',      'Voice Alert'),
            ("🌐 Webダッシュボード",  '#ff6600', 'web_dashboard.py',    'Web Dashboard'),
            ("🚁 Phase6・7シミュレーター", '#aa66ff', 'phase67_simulator.py','Phase67'),
        ]
        for text, color, script, name in notify_apps:
            btn = self._make_btn(text, color, script, name)
            notify_layout.addWidget(btn)

        notify_group.setLayout(notify_layout)
        layout.addWidget(notify_group)

        # ── 外部ツール ──
        ext_group = QGroupBox("✈️ 外部ツール")
        ext_group.setStyleSheet(
            "QGroupBox { color: #aaaaaa; border: 1px solid #555555;"
            "padding: 10px; font-size: 13px; margin-top: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; }"
        )
        ext_layout = QVBoxLayout()

        btn_qgc = QPushButton("✈️ QGroundControl")
        btn_qgc.setStyleSheet(self._btn_style('#aaaaaa'))
        btn_qgc.clicked.connect(self.launch_qgc)
        ext_layout.addWidget(btn_qgc)

        ext_group.setLayout(ext_layout)
        layout.addWidget(ext_group)

        # 全停止ボタン
        self.btn_stop_all = QPushButton("⛔ 全システム停止")
        self.btn_stop_all.setStyleSheet("""
            QPushButton {
                background-color: #330000;
                color: #ff4444;
                border: 2px solid #ff4444;
                padding: 10px;
                font-size: 15px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #550000; }
            QPushButton:pressed { background-color: #ff4444; color: #000000; }
        """)
        self.btn_stop_all.clicked.connect(self.stop_all)
        layout.addWidget(self.btn_stop_all)

        # ステータス
        self.status_label = QLabel("✅ 待機中")
        self.status_label.setStyleSheet("font-size: 13px; color: #00ff88;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # ログ
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet(
            "background-color: #050510; color: #00ff88;"
            "font-family: monospace; font-size: 11px;"
        )
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        layout.addWidget(self.log_text)

        self.log("🔥 PHENIX Launcher v3.0 起動！")
        self.log("「全システム起動」で全部一気に起動します")

    # ── ヘルパー ───────────────────────────────────

    def _btn_style(self, color):
        return (
            f"QPushButton {{"
            f"background-color: #111122; color: {color};"
            f"border: 2px solid {color}; padding: 8px;"
            f"font-size: 12px; border-radius: 5px; text-align: left; }}"
            f"QPushButton:hover {{ background-color: #222244; }}"
            f"QPushButton:pressed {{ background-color: {color}; color: #000000; }}"
        )

    def _make_btn(self, text, color, script, name):
        btn = QPushButton(text)
        btn.setStyleSheet(self._btn_style(color))
        btn.clicked.connect(lambda checked, s=script, n=name: self.launch_app(s, n))
        return btn

    # ── ログ ───────────────────────────────────────

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    # ── 起動・停止 ─────────────────────────────────

    def launch_app(self, script, name):
        if name in self.processes:
            try:
                if self.processes[name].poll() is None:
                    self.log(f"⚠️ {name} はすでに起動中です")
                    return
            except Exception:
                pass

        phenix_dir = os.path.expanduser("~/PHENIX")
        process = subprocess.Popen(['python3', script], cwd=phenix_dir)
        self.processes[name] = process
        self.log(f"✅ {name} 起動！")
        self.status_label.setText(f"✅ {name} 起動中")

    def launch_qgc(self):
        qgc_path = os.path.expanduser(
            "~/ダウンロード/QGroundControl-x86_64.AppImage"
        )
        if os.path.exists(qgc_path):
            process = subprocess.Popen([qgc_path, '--no-sandbox'])
            self.processes['QGroundControl'] = process
            self.log("✅ QGroundControl 起動！")
        else:
            self.log("⚠️ QGroundControlが見つかりません")

    def launch_all(self):
        self.log("🚀 全システム起動開始！")
        self.btn_all.setText("🚀 起動中...")

        apps = [
            ('phenix_main.py',      'Command Center'),
            ('mission_planner.py',  'Mission Planner'),
            ('mission_report.py',   'Mission Report'),
            ('voice_alert.py',      'Voice Alert'),
            ('web_dashboard.py',    'Web Dashboard'),
            ('map_viewer.py',       'Map Viewer'),
            ('data_analyzer.py',    'Data Analyzer'),
            ('radar_detection.py',  'Radar Detection'),
            ('tdoa_system.py',      'TDOA'),
            ('phase67_simulator.py','Phase67'),
        ]
        for i, (script, name) in enumerate(apps):
            QTimer.singleShot(i * 800, lambda s=script, n=name: self.launch_app(s, n))

        QTimer.singleShot(len(apps) * 800, self.all_launched)

    def all_launched(self):
        self.log("✅ 全システム起動完了！")
        self.status_label.setText("✅ 全システム稼働中")
        self.btn_all.setText("🚀 全システム起動")

    def stop_all(self):
        for name, process in self.processes.items():
            try:
                process.terminate()
                self.log(f"⛔ {name} 停止")
            except Exception:
                pass
        self.processes = {}
        self.status_label.setText("⛔ 全システム停止")
        self.log("⛔ 全システム停止完了")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PHENIXLauncher()
    window.show()
    sys.exit(app.exec())
