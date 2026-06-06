import sys
import subprocess
import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


class PHENIXSplash(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(600, 400)
        self.setStyleSheet("background-color: #0a0a1a;")

        # 画面中央に表示
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - 600) // 2,
            (screen.height() - 400) // 2
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(40, 40, 40, 40)

        # ロゴ
        self.logo = QLabel("🔥")
        self.logo.setStyleSheet("font-size: 60px;")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.logo)

        self.title = QLabel("PHENIX")
        self.title.setStyleSheet("font-size: 56px; font-weight: bold; color: #00ff88; letter-spacing: 10px;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)

        self.subtitle = QLabel("Autonomous Distributed Antenna System")
        self.subtitle.setStyleSheet("font-size: 14px; color: #444444; letter-spacing: 3px;")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle)

        self.version = QLabel("v3.2 - 2026")
        self.version.setStyleSheet("font-size: 12px; color: #333333;")
        self.version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.version)

        # スペース
        layout.addSpacing(20)

        # プログレスバー
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #111122;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #00ff88;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress)

        # ステータス
        self.status = QLabel("システム初期化中...")
        self.status.setStyleSheet("font-size: 12px; color: #444444;")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        # アニメーション用タイマー
        self.progress_value = 0
        self.step = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(50)

        self.steps = [
            (10, "システム初期化中..."),
            (25, "MAVLink接続確認中..."),
            (40, "LoRa通信モジュール起動中..."),
            (55, "GPS信号取得中..."),
            (70, "データベース接続中..."),
            (85, "センサーキャリブレーション中..."),
            (95, "起動準備完了..."),
            (100, "PHENIX起動！"),
        ]

        # フェードインアニメーション
        self.opacity = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity)
        self.fade_anim = QPropertyAnimation(self.opacity, b"opacity")
        self.fade_anim.setDuration(500)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.start()

    def update_progress(self):
        self.progress_value += 1
        self.progress.setValue(self.progress_value)

        for threshold, message in self.steps:
            if self.progress_value == threshold:
                self.status.setText(message)
                if self.progress_value == 100:
                    self.status.setStyleSheet("font-size: 12px; color: #00ff88;")

        if self.progress_value >= 100:
            self.timer.stop()
            QTimer.singleShot(500, self.launch_main)

    def launch_main(self):
        # フェードアウト
        self.fade_out = QPropertyAnimation(self.opacity, b"opacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.finished.connect(self.start_launcher)
        self.fade_out.start()

    def start_launcher(self):
        phenix_dir = os.path.expanduser("~/PHENIX")
        subprocess.Popen(['python3', 'phenix_launcher.py'], cwd=phenix_dir)
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    splash = PHENIXSplash()
    splash.show()
    sys.exit(app.exec())