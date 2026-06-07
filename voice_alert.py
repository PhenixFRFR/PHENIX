import sys
import random
import threading
import pyttsx3
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


class VoiceEngine:
    """音声エンジン"""

    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)
        self.speaking = False

        # 日本語音声を探す
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'japanese' in voice.name.lower() or 'ja' in voice.id.lower():
                self.engine.setProperty('voice', voice.id)
                break

    def speak(self, text):
        """音声で読み上げ"""
        if not self.speaking:
            self.speaking = True
            def _speak():
                self.engine.say(text)
                self.engine.runAndWait()
                self.speaking = False
            thread = threading.Thread(target=_speak, daemon=True)
            thread.start()

    def set_rate(self, rate):
        self.engine.setProperty('rate', rate)

    def set_volume(self, volume):
        self.engine.setProperty('volume', volume / 100)


class VoiceAlertSystem(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔊 PHENIX 音声アラートシステム")
        self.setGeometry(100, 100, 800, 700)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        self.voice = VoiceEngine()
        self.monitoring = False
        self.battery_threshold = 15
        self.rssi_threshold = -85
        self.drone_battery = 100
        self.rssi = -70

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🔊 PHENIX 音声アラートシステム")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 音声設定
        settings_group = QGroupBox("⚙️ 音声設定")
        settings_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        settings_layout = QGridLayout()

        settings_layout.addWidget(QLabel("読み上げ速度:"), 0, 0)
        self.rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.rate_slider.setMinimum(50)
        self.rate_slider.setMaximum(300)
        self.rate_slider.setValue(150)
        self.rate_label = QLabel("150")
        self.rate_label.setStyleSheet("color: #00aaff;")
        self.rate_slider.valueChanged.connect(
            lambda v: (self.rate_label.setText(str(v)), self.voice.set_rate(v))
        )
        settings_layout.addWidget(self.rate_slider, 0, 1)
        settings_layout.addWidget(self.rate_label, 0, 2)

        settings_layout.addWidget(QLabel("音量:"), 1, 0)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)
        self.volume_label = QLabel("100%")
        self.volume_label.setStyleSheet("color: #00aaff;")
        self.volume_slider.valueChanged.connect(
            lambda v: (self.volume_label.setText(f"{v}%"), self.voice.set_volume(v))
        )
        settings_layout.addWidget(self.volume_slider, 1, 1)
        settings_layout.addWidget(self.volume_label, 1, 2)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # テストボタン
        test_group = QGroupBox("🔊 音声テスト")
        test_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        test_layout = QGridLayout()

        alerts = [
            ("⚠️ バッテリー低下", "#ff4444", "ドローンのバッテリーが低下しています。帰還してください。"),
            ("📡 電波弱化", "#ffaa00", "電波強度が低下しています。ノードを投下します。"),
            ("🚀 ノード投下", "#ff66ff", "ノードを投下しました。通信圏を延伸します。"),
            ("👤 生存者検知", "#ff4444", "生存者を検知しました。座標を特定中です。"),
            ("✅ 帰還完了", "#00ff88", "ドローンが帰還しました。充電を開始します。"),
            ("⛔ 緊急停止", "#ff0000", "緊急停止します。全システムを停止します。"),
            ("🌐 通信切替", "#00aaff", "通信モードをロラに切り替えました。"),
            ("🛰️ Starlink接続", "#ff66ff", "スターリンクに接続しました。グローバル通信が有効です。"),
        ]

        for i, (label, color, message) in enumerate(alerts):
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #111122;
                    color: {color};
                    border: 2px solid {color};
                    padding: 10px;
                    font-size: 13px;
                    border-radius: 5px;
                }}
                QPushButton:hover {{ background-color: #222244; }}
                QPushButton:pressed {{ background-color: {color}; color: #000000; }}
            """)
            btn.clicked.connect(
                lambda checked, m=message, l=label: self.test_alert(m, l)
            )
            test_layout.addWidget(btn, i // 2, i % 2)

        test_group.setLayout(test_layout)
        layout.addWidget(test_group)

        # カスタムメッセージ
        custom_group = QGroupBox("✏️ カスタムメッセージ")
        custom_group.setStyleSheet(
            "QGroupBox { color: #00ff88; border: 1px solid #00ff88; padding: 5px; }"
        )
        custom_layout = QHBoxLayout()

        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("読み上げるメッセージを入力...")
        self.custom_input.setStyleSheet(
            "background-color: #0a0a1a; color: #00ff88; border: 1px solid #333333; padding: 5px;"
        )
        custom_layout.addWidget(self.custom_input)

        btn_speak = QPushButton("🔊 読み上げ")
        btn_speak.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                color: #00ff88;
                border: 2px solid #00ff88;
                padding: 8px;
                font-size: 13px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #005500; }
        """)
        btn_speak.clicked.connect(self.speak_custom)
        custom_layout.addWidget(btn_speak)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        # 自動監視
        monitor_group = QGroupBox("🤖 自動監視アラート")
        monitor_group.setStyleSheet(
            "QGroupBox { color: #ffaa00; border: 1px solid #ffaa00; padding: 5px; }"
        )
        monitor_layout = QVBoxLayout()

        monitor_btn_layout = QHBoxLayout()
        self.btn_monitor = QPushButton("▶️ 自動監視開始")
        self.btn_monitor.setStyleSheet("""
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
        self.btn_monitor.clicked.connect(self.toggle_monitoring)
        monitor_btn_layout.addWidget(self.btn_monitor)
        monitor_layout.addLayout(monitor_btn_layout)

        # バッテリー表示
        self.battery_label = QLabel("ドローンバッテリー: 100%")
        self.battery_label.setStyleSheet("font-size: 14px; color: #00aaff;")
        monitor_layout.addWidget(self.battery_label)

        self.battery_bar = QProgressBar()
        self.battery_bar.setValue(100)
        self.battery_bar.setStyleSheet("QProgressBar::chunk { background-color: #00aaff; }")
        monitor_layout.addWidget(self.battery_bar)

        self.rssi_label = QLabel("RSSI: -70 dBm")
        self.rssi_label.setStyleSheet("font-size: 14px; color: #00ff88;")
        monitor_layout.addWidget(self.rssi_label)

        monitor_group.setLayout(monitor_layout)
        layout.addWidget(monitor_group)

        # ログ
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet(
            "background-color: #050510; color: #00ff88; font-family: monospace; font-size: 11px;"
        )
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        layout.addWidget(self.log_text)

        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.auto_monitor)

        self.log("🔊 PHENIX 音声アラートシステム起動！")
        self.log("音声テストボタンで各アラートを確認できます")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def test_alert(self, message, label):
        self.voice.speak(message)
        self.log(f"🔊 {label}: {message}")

    def speak_custom(self):
        text = self.custom_input.text()
        if text:
            self.voice.speak(text)
            self.log(f"🔊 カスタム: {text}")

    def toggle_monitoring(self):
        self.monitoring = not self.monitoring
        if self.monitoring:
            self.monitor_timer.start(2000)
            self.btn_monitor.setText("⏹️ 自動監視停止")
            self.btn_monitor.setStyleSheet("""
                QPushButton {
                    background-color: #440000;
                    color: #ff4444;
                    border: 2px solid #ff4444;
                    padding: 10px;
                    font-size: 13px;
                    border-radius: 5px;
                }
            """)
            self.log("▶️ 自動監視開始！")
            self.voice.speak("自動監視を開始します")
        else:
            self.monitor_timer.stop()
            self.btn_monitor.setText("▶️ 自動監視開始")
            self.btn_monitor.setStyleSheet("""
                QPushButton {
                    background-color: #003300;
                    color: #00ff88;
                    border: 2px solid #00ff88;
                    padding: 10px;
                    font-size: 13px;
                    border-radius: 5px;
                }
            """)
            self.log("⏹️ 自動監視停止")

    def auto_monitor(self):
        self.drone_battery = max(0, self.drone_battery - random.uniform(0.5, 2))
        self.rssi = random.randint(-95, -55)

        self.battery_label.setText(f"ドローンバッテリー: {self.drone_battery:.0f}%")
        self.battery_bar.setValue(int(self.drone_battery))
        self.rssi_label.setText(f"RSSI: {self.rssi} dBm")

        if self.rssi_label:
            if self.rssi < self.rssi_threshold:
                self.rssi_label.setStyleSheet("font-size: 14px; color: #ff4444;")
            else:
                self.rssi_label.setStyleSheet("font-size: 14px; color: #00ff88;")

        # バッテリーアラート
        if self.drone_battery <= 5:
            self.voice.speak("緊急！バッテリーが残り5パーセントです。即時帰還してください！")
            self.log("🚨 緊急！バッテリー5%！")
        elif self.drone_battery <= 15:
            self.voice.speak("バッテリーが低下しています。帰還してください。")
            self.log("⚠️ バッテリー15%！自動帰還")
        elif self.drone_battery <= 30:
            self.voice.speak("バッテリーが30パーセントです。")
            self.log("⚠️ バッテリー30%")

        # RSSIアラート
        if self.rssi < self.rssi_threshold:
            self.voice.speak("電波強度が低下しています。ノードを投下します。")
            self.log(f"⚠️ RSSI低下: {self.rssi}dBm")

        # バッテリーリセット
        if self.drone_battery <= 0:
            self.drone_battery = 100
            self.voice.speak("充電完了。ドローンが再出撃します。")
            self.log("✅ 充電完了！再出撃")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VoiceAlertSystem()
    window.show()
    sys.exit(app.exec())