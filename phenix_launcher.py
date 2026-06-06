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
        self.setWindowTitle("🔥 PHENIX Launcher")
        self.setGeometry(400, 200, 600, 700)
        self.setStyleSheet("background-color: #0a0a1a; color: #00ff88;")

        self.processes = {}

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # ロゴ
        logo = QLabel("🔥 PHENIX")
        logo.setStyleSheet("font-size: 48px; font-weight: bold; color: #00ff88;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        subtitle = QLabel("Autonomous Distributed Antenna System")
        subtitle.setStyleSheet("font-size: 14px; color: #666666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        version = QLabel("v3.2 - 2026")
        version.setStyleSheet("font-size: 12px; color: #444444;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        # 区切り線
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
                padding: 20px;
                font-size: 20px;
                font-weight: bold;
                border-radius: 10px;
            }
            QPushButton:hover { background-color: #005500; }
            QPushButton:pressed { background-color: #00ff88; color: #000000; }
        """)
        self.btn_all.clicked.connect(self.launch_all)
        layout.addWidget(self.btn_all)

        # 個別起動ボタン
        apps_group = QGroupBox("個別起動")
        apps_group.setStyleSheet("QGroupBox { color: #00ff88; border: 1px solid #333333; padding: 10px; font-size: 14px; }")
        apps_layout = QVBoxLayout()

        # Command Center
        btn_cc = QPushButton("🖥️ Command Center v3.2")
        btn_cc.setStyleSheet(self.get_btn_style('#00ff88'))
        btn_cc.clicked.connect(lambda: self.launch_app('phenix_main.py', 'Command Center'))
        apps_layout.addWidget(btn_cc)

        # Map Viewer
        btn_map = QPushButton("🗺️ マップビューア")
        btn_map.setStyleSheet(self.get_btn_style('#00aaff'))
        btn_map.clicked.connect(lambda: self.launch_app('map_viewer.py', 'Map Viewer'))
        apps_layout.addWidget(btn_map)

        # Data Analyzer
        btn_data = QPushButton("📊 データ分析ツール")
        btn_data.setStyleSheet(self.get_btn_style('#ffaa00'))
        btn_data.clicked.connect(lambda: self.launch_app('data_analyzer.py', 'Data Analyzer'))
        apps_layout.addWidget(btn_data)

        # QGroundControl
        btn_qgc = QPushButton("✈️ QGroundControl")
        btn_qgc.setStyleSheet(self.get_btn_style('#ff66ff'))
        btn_qgc.clicked.connect(self.launch_qgc)
        apps_layout.addWidget(btn_qgc)

        apps_group.setLayout(apps_layout)
        layout.addWidget(apps_group)

        # 全停止ボタン
        self.btn_stop_all = QPushButton("⛔ 全システム停止")
        self.btn_stop_all.setStyleSheet("""
            QPushButton {
                background-color: #330000;
                color: #ff4444;
                border: 2px solid #ff4444;
                padding: 10px;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #550000; }
            QPushButton:pressed { background-color: #ff4444; color: #000000; }
        """)
        self.btn_stop_all.clicked.connect(self.stop_all)
        layout.addWidget(self.btn_stop_all)

        # ステータス
        self.status_label = QLabel("✅ 待機中")
        self.status_label.setStyleSheet("font-size: 14px; color: #00ff88;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # ログ
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet("background-color: #050510; color: #00ff88; font-family: monospace; font-size: 11px;")
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        layout.addWidget(self.log_text)

        self.log("🔥 PHENIX Launcher 起動！")
        self.log("「全システム起動」で全部一気に起動します")

    def get_btn_style(self, color):
        return f"""
            QPushButton {{
                background-color: #111122;
                color: {color};
                border: 2px solid {color};
                padding: 12px;
                font-size: 14px;
                border-radius: 5px;
                text-align: left;
            }}
            QPushButton:hover {{ background-color: #222244; }}
            QPushButton:pressed {{ background-color: {color}; color: #000000; }}
        """

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def launch_app(self, script, name):
        if name in self.processes:
            try:
                if self.processes[name].poll() is None:
                    self.log(f"⚠️ {name} はすでに起動中です")
                    return
            except:
                pass

        phenix_dir = os.path.expanduser("~/PHENIX")
        process = subprocess.Popen(
            ['python3', script],
            cwd=phenix_dir
        )
        self.processes[name] = process
        self.log(f"✅ {name} 起動！")
        self.status_label.setText(f"✅ {name} 起動中")

    def launch_qgc(self):
        qgc_path = os.path.expanduser("~/ダウンロード/QGroundControl-x86_64.AppImage")
        if os.path.exists(qgc_path):
            process = subprocess.Popen([qgc_path, '--no-sandbox'])
            self.processes['QGroundControl'] = process
            self.log("✅ QGroundControl 起動！")
        else:
            self.log("⚠️ QGroundControlが見つかりません")

    def launch_all(self):
        self.log("🚀 全システム起動開始！")
        self.btn_all.setText("🚀 起動中...")

        self.launch_app('phenix_main.py', 'Command Center')
        QTimer.singleShot(1000, lambda: self.launch_app('map_viewer.py', 'Map Viewer'))
        QTimer.singleShot(2000, lambda: self.launch_app('data_analyzer.py', 'Data Analyzer'))

        self.log("✅ 全システム起動完了！")
        self.status_label.setText("✅ 全システム稼働中")
        self.btn_all.setText("🚀 全システム起動")

    def stop_all(self):
        for name, process in self.processes.items():
            try:
                process.terminate()
                self.log(f"⛔ {name} 停止")
            except:
                pass
        self.processes = {}
        self.status_label.setText("⛔ 全システム停止")
        self.log("⛔ 全システム停止完了")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PHENIXLauncher()
    window.show()
    sys.exit(app.exec())