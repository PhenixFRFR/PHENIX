import sys
import random
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from lora_manager import LoRaManager
from mavlink_bridge import MAVLinkBridge


# ─────────────────────────────────────────
#  ドローンごとのアクセントカラー
# ─────────────────────────────────────────
DRONE_COLORS = ["#00ff88", "#00aaff", "#ff66ff", "#ffaa00", "#ff6666", "#66ffff"]

# ドローンの状態定数
STATUS_STANDBY   = "待機中"
STATUS_ACTIVE    = "運用中"
STATUS_RETURNING = "帰還中"
STATUS_CHARGING  = "充電中"
STATUS_EMERGENCY = "緊急停止"


# ─────────────────────────────────────────
#  RSSI グラフ
# ─────────────────────────────────────────
class RSSIGraph(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(4, 2), facecolor='#1a1a2e')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#0a0a1a')
        self.ax.tick_params(colors='#00ff88')
        for spine in self.ax.spines.values():
            spine.set_color('#00ff88')
        self.ax.set_ylim(-120, -40)
        self.ax.set_title('RSSI履歴', color='#00ff88', fontsize=9)
        super().__init__(self.fig)
        self.rssi_data = []

    def update_graph(self, rssi):
        self.rssi_data.append(rssi)
        if len(self.rssi_data) > 60:
            self.rssi_data.pop(0)
        self.ax.clear()
        self.ax.set_facecolor('#0a0a1a')
        self.ax.set_ylim(-120, -40)
        self.ax.set_title('RSSI履歴 (直近60秒)', color='#00ff88', fontsize=9)
        self.ax.tick_params(colors='#00ff88')
        for spine in self.ax.spines.values():
            spine.set_color('#00ff88')
        self.ax.axhline(y=-85, color='#ff4444', linestyle='--', label='-85dBm')
        colors = ['#ff4444' if r < -85 else '#00ff88' for r in self.rssi_data]
        self.ax.bar(range(len(self.rssi_data)), self.rssi_data, color=colors, alpha=0.7)
        self.ax.legend(facecolor='#1a1a2e', labelcolor='#00ff88', fontsize=7)
        self.draw()


# ─────────────────────────────────────────
#  母艦ドック（待機ドローン管理パネル）
# ─────────────────────────────────────────
class MotherDockPanel(QWidget):
    """
    母艦に待機しているドローンの一覧を表示。
    swap_requested シグナルで「このドローンを出撃させて」と通知する。
    """
    swap_requested = pyqtSignal(int)   # drone_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.standby_drones = {}   # drone_id -> battery%

        self.setStyleSheet("background-color: #12122a;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QLabel("🛳️ 母艦ドック — 待機ドローン")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #00ffff;"
                             "border: 1px solid #00ffff; padding: 4px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(3)
        layout.addLayout(self.list_layout)
        layout.addStretch()

        self._rows = {}   # drone_id -> QWidget row

    def add_drone(self, drone_id: int, battery: int, color: str):
        """ドローンをドックに追加（帰還完了時に呼ぶ）"""
        if drone_id in self._rows:
            return
        self.standby_drones[drone_id] = battery

        row = QWidget()
        row.setStyleSheet(f"background-color: #1a1a2e; border: 1px solid {color}; border-radius: 4px;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(6, 3, 6, 3)

        lbl = QLabel(f"🚁 ドローン {drone_id}　バッテリー: {battery}%")
        lbl.setStyleSheet(f"color: {color}; font-size: 12px;")
        row_layout.addWidget(lbl, stretch=1)

        btn = QPushButton("🚀 出撃")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #003300; color: {color};
                border: 1px solid {color}; padding: 4px 10px;
                font-size: 11px; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {color}; color: #000000; }}
        """)
        btn.clicked.connect(lambda _, did=drone_id: self.swap_requested.emit(did))
        row_layout.addWidget(btn)

        self.list_layout.addWidget(row)
        self._rows[drone_id] = (row, lbl)

    def remove_drone(self, drone_id: int):
        """ドローンをドックから取り出す（出撃時）"""
        if drone_id not in self._rows:
            return
        row, _ = self._rows.pop(drone_id)
        row.setParent(None)
        self.standby_drones.pop(drone_id, None)

    def update_battery(self, drone_id: int, battery: int):
        if drone_id in self._rows:
            _, lbl = self._rows[drone_id]
            color = DRONE_COLORS[(drone_id - 1) % len(DRONE_COLORS)]
            lbl.setText(f"🚁 ドローン {drone_id}　バッテリー: {battery}%")
            self.standby_drones[drone_id] = battery

    def has_available_drone(self) -> bool:
        """出撃可能（バッテリー30%以上）な待機ドローンがいるか"""
        return any(b >= 30 for b in self.standby_drones.values())

    def best_drone_id(self) -> int | None:
        """最もバッテリーが多い待機ドローンのIDを返す"""
        if not self.standby_drones:
            return None
        return max(self.standby_drones, key=lambda k: self.standby_drones[k])


# ─────────────────────────────────────────
#  1機分のドローン操作パネル
# ─────────────────────────────────────────
class DronePanelWidget(QWidget):
    """
    シグナル:
      return_to_dock(drone_id)   帰還完了をメインに通知
      swap_needed(drone_id)      入れ替え推奨をメインに通知
    """
    return_to_dock = pyqtSignal(int)
    swap_needed    = pyqtSignal(int)

    def __init__(self, drone_id: int, color: str = "#00ff88", parent=None):
        super().__init__(parent)
        self.drone_id = drone_id
        self.color    = color
        self.node_count          = 3
        self.countdown_value     = 0
        self.current_mode        = STATUS_STANDBY
        self.emergency           = False
        self.auto_return_enabled = True
        self.circle_radius       = 100
        self.follow_altitude     = 30
        self.auto_return_triggered = False
        self.swap_notified       = False   # 入れ替え推奨を既に出したか
        self.blink_state         = False
        self._simulated_battery  = 100    # デモ用内部バッテリー

        self.lora    = LoRaManager()
        self.mavlink = MAVLinkBridge()
        self.mavlink.connect()

        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.blink_recommend_button)

        self._build_ui()

    # ── UI 構築 ────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # タイトル行
        title_row = QHBoxLayout()
        self.title_label = QLabel(f"🚁 ドローン {self.drone_id}")
        self.title_label.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {self.color};"
            f"border: 2px solid {self.color}; padding: 4px; border-radius: 4px;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_row.addWidget(self.title_label, stretch=1)

        self.status_badge = QLabel(f"● {STATUS_STANDBY}")
        self.status_badge.setStyleSheet("font-size: 12px; color: #ffaa00; font-weight: bold;")
        title_row.addWidget(self.status_badge)
        layout.addLayout(title_row)

        # 接続状態
        self.connection_status = QLabel("🔗 MAVLink: 接続中 | LoRa: 待機中")
        self.connection_status.setStyleSheet("font-size: 11px; color: #00aaff;")
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.connection_status)

        # ── 操作ボタン ──
        control_group = QGroupBox("🎮 操作パネル")
        control_group.setStyleSheet(
            f"QGroupBox {{ color: {self.color}; border: 1px solid {self.color}; padding: 3px; }}")
        cg = QGridLayout()
        cg.setSpacing(3)

        def bs(bg, fg):
            return (f"QPushButton {{ background-color:{bg}; color:{fg};"
                    f"border:1px solid {fg}; padding:5px; font-size:11px; border-radius:4px; }}"
                    f"QPushButton:hover {{ background-color:{fg}; color:#000000; }}")

        self.btn_follow    = QPushButton("🟢 追従");    self.btn_follow.setStyleSheet(bs("#004400","#00ff88"))
        self.btn_hover_btn = QPushButton("🔴 解除");    self.btn_hover_btn.setStyleSheet(bs("#440000","#ff4444"))
        self.btn_circle    = QPushButton("🔵 旋回");    self.btn_circle.setStyleSheet(bs("#000044","#00aaff"))
        self.btn_return    = QPushButton("🟡 帰還");    self.btn_return.setStyleSheet(bs("#444400","#ffaa00"))
        self.btn_drop      = QPushButton("🚀 ノード投下"); self.btn_drop.setStyleSheet(bs("#440044","#ff66ff"))
        self.btn_recommend_drop = QPushButton("💡 投下推奨"); self.btn_recommend_drop.setStyleSheet(bs("#333300","#888800"))

        # 緊急停止ボタン（帰還 or 即停止ダイアログ）
        self.btn_emergency = QPushButton("⛔ 緊急停止")
        self.btn_emergency.setStyleSheet("""
            QPushButton { background-color:#ff0000; color:#ffffff;
                border:2px solid #ffffff; padding:5px; font-size:11px;
                font-weight:bold; border-radius:4px; }
            QPushButton:hover { background-color:#cc0000; }
        """)

        self.btn_follow.clicked.connect(self.start_follow_mode)
        self.btn_hover_btn.clicked.connect(self.stop_follow_mode)
        self.btn_circle.clicked.connect(self.start_circle_mode)
        self.btn_return.clicked.connect(self.start_return_mode)
        self.btn_emergency.clicked.connect(self.emergency_dialog)
        self.btn_drop.clicked.connect(self.manual_drop)
        self.btn_recommend_drop.clicked.connect(self.recommend_drop_ack)

        cg.addWidget(self.btn_follow,         0, 0)
        cg.addWidget(self.btn_hover_btn,      0, 1)
        cg.addWidget(self.btn_circle,         0, 2)
        cg.addWidget(self.btn_return,         0, 3)
        cg.addWidget(self.btn_emergency,      1, 0, 1, 2)
        cg.addWidget(self.btn_drop,           1, 2)
        cg.addWidget(self.btn_recommend_drop, 1, 3)
        control_group.setLayout(cg)
        layout.addWidget(control_group)

        # ── スライダー ──
        slider_group = QGroupBox("⚙️ 飛行パラメーター")
        slider_group.setStyleSheet(
            f"QGroupBox {{ color: {self.color}; border: 1px solid {self.color}; padding: 3px; }}")
        sg = QGridLayout(); sg.setSpacing(3)

        sg.addWidget(self._lbl("🔵 旋回半径:", "#00aaff"), 0, 0)
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(1, 1000); self.radius_slider.setValue(100)
        self.radius_slider.valueChanged.connect(self.update_radius)
        sg.addWidget(self.radius_slider, 0, 1)
        self.radius_value = self._lbl("100 m", "#00aaff")
        sg.addWidget(self.radius_value, 0, 2)

        sg.addWidget(self._lbl("🟢 追従高度:", "#00ff88"), 1, 0)
        self.altitude_slider = QSlider(Qt.Orientation.Horizontal)
        self.altitude_slider.setRange(1, 500); self.altitude_slider.setValue(30)
        self.altitude_slider.valueChanged.connect(self.update_altitude)
        sg.addWidget(self.altitude_slider, 1, 1)
        self.altitude_value = self._lbl("30 m", "#00ff88")
        sg.addWidget(self.altitude_value, 1, 2)

        sg.addWidget(self._lbl("🔒 自動帰還(15%):", "#ffaa00"), 0, 3)
        self.btn_auto_return = QPushButton("✅ ON")
        self.btn_auto_return.setStyleSheet(bs("#004400","#00ff88"))
        self.btn_auto_return.clicked.connect(self.toggle_auto_return)
        sg.addWidget(self.btn_auto_return, 0, 4)

        # 入れ替えボタン（普段は非表示）
        self.btn_swap = QPushButton("🔄 待機機と入れ替え")
        self.btn_swap.setStyleSheet("""
            QPushButton { background-color:#1a3333; color:#00ffff;
                border:2px solid #00ffff; padding:5px; font-size:11px;
                font-weight:bold; border-radius:4px; }
            QPushButton:hover { background-color:#00ffff; color:#000000; }
        """)
        self.btn_swap.setVisible(False)
        self.btn_swap.clicked.connect(self.request_swap)
        sg.addWidget(self.btn_swap, 1, 3, 1, 2)

        slider_group.setLayout(sg)
        layout.addWidget(slider_group)

        # モード表示
        self.mode_label = QLabel("現在のモード: 待機中")
        self.mode_label.setStyleSheet("font-size: 13px; color: #ffaa00; font-weight: bold;")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.mode_label)

        # ── データグリッド ──
        data_layout = QHBoxLayout()

        # RSSI
        rg = QGroupBox("📡 LoRa")
        rg.setStyleSheet(f"QGroupBox {{ color:{self.color}; border:1px solid {self.color}; padding:3px; }}")
        rv = QVBoxLayout()
        self.rssi_label      = self._lbl("RSSI: --- dBm", self.color, 13)
        self.snr_label       = self._lbl("SNR: --- dB",   "#00aaff")
        self.countdown_label = self._lbl("投下まで: 待機中", "#ffaa00")
        self.node_count_label= self._lbl("ノード残数: 3個", "#ffaa00")
        for w in [self.rssi_label, self.snr_label, self.countdown_label, self.node_count_label]:
            rv.addWidget(w)
        rg.setLayout(rv); data_layout.addWidget(rg)

        # バッテリー
        bg = QGroupBox("🔋 バッテリー")
        bg.setStyleSheet(f"QGroupBox {{ color:{self.color}; border:1px solid {self.color}; padding:3px; }}")
        bv = QVBoxLayout()
        self.bat_mother_label = self._lbl("母艦: 100%", "#00ff88")
        self.battery_mother   = self._bar("#00ff88"); self.battery_mother.setValue(100)
        self.bat_drone_label  = self._lbl("ドローン: 100%", "#00aaff")
        self.battery_drone    = self._bar("#00aaff"); self.battery_drone.setValue(100)
        self.bat_node_label   = self._lbl("ノード: 100%", "#ffaa00")
        self.battery_node     = self._bar("#ffaa00"); self.battery_node.setValue(100)
        for w in [self.bat_mother_label, self.battery_mother,
                  self.bat_drone_label,  self.battery_drone,
                  self.bat_node_label,   self.battery_node]:
            bv.addWidget(w)
        bg.setLayout(bv); data_layout.addWidget(bg)

        # ドローン状態
        dg = QGroupBox("🚁 状態(MAVLink)")
        dg.setStyleSheet(f"QGroupBox {{ color:{self.color}; border:1px solid {self.color}; padding:3px; }}")
        dv = QVBoxLayout()
        self.drone_mode_label = self._lbl("モード: ---",   self.color)
        self.drone_armed      = self._lbl("アーム: ---",   "#ff4444")
        self.drone_alt        = self._lbl("高度: --- m",   "#00aaff")
        self.drone_speed      = self._lbl("速度: --- km/h","#00aaff")
        self.drone_heading    = self._lbl("方位: --- °",   "#aa66ff")
        self.drone_sats       = self._lbl("衛星: --- 機",  "#66ff66")
        for w in [self.drone_mode_label, self.drone_armed, self.drone_alt,
                  self.drone_speed, self.drone_heading, self.drone_sats]:
            dv.addWidget(w)
        dg.setLayout(dv); data_layout.addWidget(dg)

        # センサー＋GPS＋アラート
        sg2 = QGroupBox("🌡️ センサー / GPS")
        sg2.setStyleSheet(f"QGroupBox {{ color:{self.color}; border:1px solid {self.color}; padding:3px; }}")
        sv = QVBoxLayout()
        self.temperature    = self._lbl("気温: --- ℃",   "#ff6666")
        self.humidity       = self._lbl("湿度: --- %",    "#66aaff")
        self.pressure_label = self._lbl("気圧: --- hPa",  "#66ff66")
        self.drone_gps      = self._lbl("ドローン: ---, ---", "#00aaff")
        self.mother_gps     = self._lbl("母艦: ---, ---", self.color)
        self.alert_label    = self._lbl("✅ 正常稼働中",  self.color)
        for w in [self.temperature, self.humidity, self.pressure_label,
                  self.drone_gps, self.mother_gps, self.alert_label]:
            sv.addWidget(w)
        sg2.setLayout(sv); data_layout.addWidget(sg2)

        layout.addLayout(data_layout)

        # RSSI グラフ
        self.rssi_graph = RSSIGraph()
        self.rssi_graph.setMaximumHeight(130)
        layout.addWidget(self.rssi_graph)

        # ログ
        lg = QGroupBox("📋 ログ")
        lg.setStyleSheet(f"QGroupBox {{ color:{self.color}; border:1px solid {self.color}; padding:3px; }}")
        lv = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet(
            f"background-color:#0a0a1a; color:{self.color}; font-family:monospace; font-size:11px;")
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(90)
        lv.addWidget(self.log_text)
        lg.setLayout(lv)
        layout.addWidget(lg)

        self.db_stats = self._lbl("DB: 0件", "#66ff66", 11)
        layout.addWidget(self.db_stats)

    # ── ヘルパー ────────────────────────────
    def _lbl(self, text, color, size=12):
        w = QLabel(text)
        w.setStyleSheet(f"font-size:{size}px; color:{color};")
        return w

    def _bar(self, color):
        b = QProgressBar()
        b.setStyleSheet(f"QProgressBar::chunk {{ background-color:{color}; }}")
        return b

    def add_log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{ts}] {msg}")

    def _set_status(self, status: str):
        self.current_mode = status
        colors = {
            STATUS_STANDBY:   "#ffaa00",
            STATUS_ACTIVE:    "#00ff88",
            STATUS_RETURNING: "#00aaff",
            STATUS_CHARGING:  "#66ff66",
            STATUS_EMERGENCY: "#ff0000",
        }
        c = colors.get(status, "#ffffff")
        self.status_badge.setText(f"● {status}")
        self.status_badge.setStyleSheet(f"font-size:12px; color:{c}; font-weight:bold;")

    # ── スライダー ──────────────────────────
    def update_radius(self, v):
        self.circle_radius = v
        self.radius_value.setText(f"{v} m")

    def update_altitude(self, v):
        self.follow_altitude = v
        self.altitude_value.setText(f"{v} m")

    def toggle_auto_return(self):
        self.auto_return_enabled = not self.auto_return_enabled
        if self.auto_return_enabled:
            self.btn_auto_return.setText("✅ ON")
            self.add_log("🔒 自動帰還（15%）：ON")
        else:
            self.btn_auto_return.setText("❌ OFF")
            self.add_log("🔓 自動帰還（15%）：OFF")

    # ── 飛行モード ──────────────────────────
    def start_follow_mode(self):
        self.mavlink.set_mode("FOLLOW")
        self._set_status(STATUS_ACTIVE)
        self.mode_label.setText(f"現在のモード: 🟢 追従モード（高度: {self.follow_altitude}m）")
        self.mode_label.setStyleSheet("font-size:13px; color:#00ff88; font-weight:bold;")
        self.add_log(f"🟢 追従モード開始！高度: {self.follow_altitude}m")
        self.emergency = False
        self.auto_return_triggered = False
        self.swap_notified = False
        self.btn_swap.setVisible(False)

    def stop_follow_mode(self):
        self.mavlink.set_mode("LOITER")
        self._set_status(STATUS_STANDBY)
        self.mode_label.setText("現在のモード: 🔴 追従解除（ホバリング）")
        self.mode_label.setStyleSheet("font-size:13px; color:#ff4444; font-weight:bold;")
        self.add_log("🔴 追従解除！ドローンはホバリング中")

    def start_circle_mode(self):
        self.mavlink.set_mode("AUTO")
        self._set_status(STATUS_ACTIVE)
        self.mode_label.setText(f"現在のモード: 🔵 旋回モード（半径: {self.circle_radius}m）")
        self.mode_label.setStyleSheet("font-size:13px; color:#00aaff; font-weight:bold;")
        self.add_log(f"🔵 旋回モード開始！半径: {self.circle_radius}m")

    def start_return_mode(self):
        self.mavlink.set_mode("GUIDED")
        self._set_status(STATUS_RETURNING)
        self.mode_label.setText("現在のモード: 🟡 帰還モード")
        self.mode_label.setStyleSheet("font-size:13px; color:#ffaa00; font-weight:bold;")
        self.add_log("🟡 帰還モード開始！ドローンがドックに帰還します")

    # ── 緊急停止（確認ダイアログ） ──────────
    def emergency_dialog(self):
        dlg = QMessageBox(self)
        dlg.setWindowTitle(f"⛔ 緊急停止 — ドローン {self.drone_id}")
        dlg.setText(
            f"<b style='color:#ff4444'>ドローン {self.drone_id} の緊急停止を実行しますか？</b><br><br>"
            "操作を選択してください。"
        )
        dlg.setStyleSheet(
            "QMessageBox { background-color:#1a1a2e; color:#ffffff; }"
            "QLabel { color:#ffffff; font-size:13px; }"
            "QPushButton { padding:6px 14px; font-size:12px; border-radius:4px; }"
        )
        btn_return   = dlg.addButton("🟡 母艦へ帰還", QMessageBox.ButtonRole.AcceptRole)
        btn_stop     = dlg.addButton("⛔ 即時停止",   QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel   = dlg.addButton("キャンセル",    QMessageBox.ButtonRole.RejectRole)
        btn_return.setStyleSheet("background-color:#444400; color:#ffaa00; border:1px solid #ffaa00;")
        btn_stop.setStyleSheet(  "background-color:#ff0000; color:#ffffff; border:2px solid #ffffff;")
        btn_cancel.setStyleSheet("background-color:#333333; color:#aaaaaa; border:1px solid #aaaaaa;")
        dlg.exec()

        clicked = dlg.clickedButton()
        if clicked == btn_return:
            self.start_return_mode()
            self.add_log("🟡 緊急停止→帰還を選択。母艦へ誘導中...")
        elif clicked == btn_stop:
            self._do_emergency_stop()

    def _do_emergency_stop(self):
        self.emergency = True
        self.mavlink.disarm()
        self._set_status(STATUS_EMERGENCY)
        self.mode_label.setText("現在のモード: ⛔ 緊急停止！")
        self.mode_label.setStyleSheet("font-size:13px; color:#ff0000; font-weight:bold;")
        self.alert_label.setText("⛔ 緊急停止実行！")
        self.alert_label.setStyleSheet("font-size:12px; color:#ff0000;")
        self.add_log("⛔ 緊急停止！全システム停止")

    # ── ノード投下 ──────────────────────────
    def manual_drop(self):
        if self.node_count > 0:
            self.node_count -= 1
            self.node_count_label.setText(f"ノード残数: {self.node_count}個")
            self.add_log(f"🚀 手動ノード投下！残り{self.node_count}個")
        else:
            self.add_log("❌ ノード残数が0です！")
            self.alert_label.setText("❌ ノード残数0！")
            self.alert_label.setStyleSheet("font-size:12px; color:#ff4444;")

    def recommend_drop(self):
        if not self.blink_timer.isActive():
            self.blink_timer.start(500)
            self.add_log("💡 投下推奨！オペレーターの判断を待っています")

    def recommend_drop_ack(self):
        self.blink_timer.stop()
        self.btn_recommend_drop.setText("💡 投下推奨")
        self.manual_drop()

    def blink_recommend_button(self):
        if self.blink_state:
            self.btn_recommend_drop.setStyleSheet(
                "QPushButton { background-color:#ffff00; color:#000000;"
                "border:2px solid #ffff00; padding:5px; font-size:11px;"
                "font-weight:bold; border-radius:4px; }")
            self.btn_recommend_drop.setText("💡 投下推奨 !")
        else:
            self.btn_recommend_drop.setStyleSheet(
                "QPushButton { background-color:#333300; color:#888800;"
                "border:1px solid #888800; padding:5px; font-size:11px; border-radius:4px; }"
                "QPushButton:hover { background-color:#ffff00; color:#000000; }")
            self.btn_recommend_drop.setText("💡 投下推奨")
        self.blink_state = not self.blink_state

    # ── 入れ替えシステム ────────────────────
    def request_swap(self):
        """入れ替えボタン押下 → メインに通知"""
        self.swap_needed.emit(self.drone_id)
        self.btn_swap.setVisible(False)

    def notify_swap_available(self):
        """メインから「待機機あり」を受け取りボタンを表示・点滅"""
        if not self.swap_notified:
            self.swap_notified = True
            self.btn_swap.setVisible(True)
            self.add_log("🔄 待機ドローンへの入れ替えが可能です！承認してください")
            self.alert_label.setText("🔄 入れ替え推奨！")
            self.alert_label.setStyleSheet("font-size:12px; color:#00ffff; font-weight:bold;")

    # ── 自動帰還チェック ────────────────────
    def check_auto_return(self, bat: int):
        if self.auto_return_enabled and bat <= 15 and not self.auto_return_triggered:
            self.auto_return_triggered = True
            self.start_return_mode()
            self.alert_label.setText("⚠️ バッテリー低下！自動帰還中")
            self.alert_label.setStyleSheet("font-size:12px; color:#ff4444;")
            self.add_log(f"⚠️ バッテリー{bat}%！自動帰還開始！")

    # ── 入れ替え推奨チェック ────────────────
    def check_swap_needed(self, bat: int, dock_has_drone: bool):
        """バッテリー30%以下 & 待機機あり → 入れ替え推奨"""
        if (bat <= 30 and dock_has_drone
                and not self.swap_notified
                and not self.auto_return_triggered
                and not self.emergency):
            self.swap_needed.emit(self.drone_id)

    # ── 定期更新 ────────────────────────────
    def update_display(self):
        if self.emergency:
            return

        rssi = random.randint(-95, -55)
        snr  = random.uniform(-5, 10)
        self.rssi_label.setText(f"RSSI: {rssi} dBm")
        self.snr_label.setText(f"SNR: {snr:.1f} dB")
        self.rssi_graph.update_graph(rssi)

        event = self.lora.check_rssi(rssi)
        self.lora.save_lora_data(rssi, snr, f"PHENIX D{self.drone_id}", event)

        if rssi < -85:
            self.rssi_label.setStyleSheet(f"font-size:13px; color:#ff4444;")
            self.countdown_value += 1
            remaining = max(0, 7 - self.countdown_value)
            self.countdown_label.setText(f"⚠️ 投下まで: {remaining}秒...")
            self.alert_label.setText("⚠️ 電波弱化検知！")
            self.alert_label.setStyleSheet("font-size:12px; color:#ff4444;")
            self.recommend_drop()
            if self.countdown_value >= 7 and self.node_count > 0:
                self.node_count -= 1
                self.node_count_label.setText(f"ノード残数: {self.node_count}個")
                self.add_log(f"🚀 自動ノード投下！残り{self.node_count}個")
                self.countdown_value = 0
        else:
            self.rssi_label.setStyleSheet(f"font-size:13px; color:{self.color};")
            self.countdown_label.setText("投下まで: 待機中")
            self.countdown_value = 0
            self.blink_timer.stop()
            self.btn_recommend_drop.setText("💡 投下推奨")
            if not self.emergency and not self.auto_return_triggered and not self.swap_notified:
                self.alert_label.setText("✅ 正常稼働中")
                self.alert_label.setStyleSheet(f"font-size:12px; color:{self.color};")

        drone  = self.mavlink.get_drone_telemetry()
        mother = self.mavlink.get_mother_telemetry()

        if drone:
            self.drone_mode_label.setText(f"モード: {drone['mode']}")
            self.drone_armed.setText(f"アーム: {'✅ ON' if drone['armed'] else '❌ OFF'}")
            self.drone_alt.setText(f"高度: {drone['altitude']:.1f} m")
            self.drone_speed.setText(f"速度: {drone['speed']:.1f} km/h")
            self.drone_heading.setText(f"方位: {drone['heading']:.0f} °")
            self.drone_sats.setText(f"衛星: {drone['satellites']} 機")
            bat = drone['battery']
            self.battery_drone.setValue(bat)
            self.bat_drone_label.setText(f"ドローン: {bat}%")
            self.drone_gps.setText(f"ドローン: {drone['lat']:.4f}, {drone['lng']:.4f}")
            self.check_auto_return(bat)

        if mother:
            self.battery_mother.setValue(mother['battery'])
            self.bat_mother_label.setText(f"母艦: {mother['battery']}%")
            self.mother_gps.setText(f"母艦: {mother['lat']:.4f}, {mother['lng']:.4f}")
            self.mavlink.save_telemetry(drone, mother)

        temp     = random.uniform(20, 35)
        humid    = random.uniform(40, 80)
        pressure = random.uniform(1010, 1020)
        self.temperature.setText(f"気温: {temp:.1f} ℃")
        self.humidity.setText(f"湿度: {humid:.1f} %")
        self.pressure_label.setText(f"気圧: {pressure:.1f} hPa")

        stats = self.lora.get_stats()
        self.db_stats.setText(f"DB: {stats['total_records']}件記録済み")

    def init_log(self):
        self.add_log(f"🔥 ドローン {self.drone_id} 起動！")
        self.add_log("✅ MAVLink Bridge 接続完了")
        self.add_log("✅ LoRa Manager 初期化完了")
        self.add_log("🔒 自動帰還（15%）：ON")


# ─────────────────────────────────────────
#  メインウィンドウ
# ─────────────────────────────────────────
class PHENIXMain(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PHENIX Command Center v3.2 — マルチドローン統合システム")
        self.setGeometry(100, 100, 1600, 980)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        self.drone_panels  = []   # アクティブパネルリスト
        self.drone_count   = 0
        self.next_drone_id = 1

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setSpacing(6)
        root_layout.setContentsMargins(6, 6, 6, 6)

        # ── グローバルヘッダー ──
        header = QHBoxLayout()

        title = QLabel("🔥 PHENIX Command Center v3.2 — マルチドローン")
        title.setStyleSheet("font-size: 19px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(title, stretch=3)

        self.btn_add = QPushButton("＋ ドローン追加")
        self.btn_add.setStyleSheet("""
            QPushButton { background-color:#003333; color:#00ffff;
                border:2px solid #00ffff; padding:7px 14px;
                font-size:13px; font-weight:bold; border-radius:6px; }
            QPushButton:hover { background-color:#00ffff; color:#000000; }
        """)
        self.btn_add.clicked.connect(self.add_active_drone)
        header.addWidget(self.btn_add)

        self.btn_add_standby = QPushButton("🛳️ 待機機追加")
        self.btn_add_standby.setStyleSheet("""
            QPushButton { background-color:#002233; color:#00aaff;
                border:2px solid #00aaff; padding:7px 14px;
                font-size:13px; font-weight:bold; border-radius:6px; }
            QPushButton:hover { background-color:#00aaff; color:#000000; }
        """)
        self.btn_add_standby.clicked.connect(self.add_standby_drone)
        header.addWidget(self.btn_add_standby)

        self.btn_all_emergency = QPushButton("⛔ 全機緊急停止")
        self.btn_all_emergency.setStyleSheet("""
            QPushButton { background-color:#ff0000; color:#ffffff;
                border:3px solid #ffffff; padding:7px 14px;
                font-size:13px; font-weight:bold; border-radius:6px; }
            QPushButton:hover { background-color:#cc0000; }
        """)
        self.btn_all_emergency.clicked.connect(self.all_emergency_dialog)
        header.addWidget(self.btn_all_emergency)

        root_layout.addLayout(header)

        # ── メインエリア（左:アクティブパネル / 右:ドック） ──
        main_area = QHBoxLayout()
        main_area.setSpacing(8)

        # アクティブドローンスクロールエリア
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("QScrollArea { border:none; background-color:#1a1a2e; }")

        self.panels_container = QWidget()
        self.panels_layout = QHBoxLayout(self.panels_container)
        self.panels_layout.setSpacing(8)
        self.panels_layout.setContentsMargins(4, 4, 4, 4)
        self.panels_layout.addStretch()
        self.scroll.setWidget(self.panels_container)
        main_area.addWidget(self.scroll, stretch=4)

        # 母艦ドックパネル
        self.dock = MotherDockPanel()
        self.dock.setFixedWidth(260)
        self.dock.swap_requested.connect(self.deploy_standby_drone)
        main_area.addWidget(self.dock, stretch=0)

        root_layout.addLayout(main_area)

        # グローバルタイマー
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all)
        self.timer.start(1000)

        # 起動時にアクティブドローン1機追加
        self.add_active_drone()

    # ── ドローン追加 ────────────────────────
    def _next_color(self) -> str:
        return DRONE_COLORS[(self.next_drone_id - 1) % len(DRONE_COLORS)]

    def add_active_drone(self):
        color  = self._next_color()
        drone_id = self.next_drone_id
        self.next_drone_id += 1
        self.drone_count += 1

        panel = DronePanelWidget(drone_id=drone_id, color=color)
        panel.setMinimumWidth(670)
        panel.swap_needed.connect(self.on_swap_needed)

        if self.drone_count > 1:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.VLine)
            sep.setStyleSheet("color:#333355;")
            self.panels_layout.insertWidget(self.panels_layout.count() - 1, sep)

        self.panels_layout.insertWidget(self.panels_layout.count() - 1, panel)
        self.drone_panels.append(panel)
        panel.init_log()
        self._update_title()

    def add_standby_drone(self):
        color    = self._next_color()
        drone_id = self.next_drone_id
        self.next_drone_id += 1
        self.dock.add_drone(drone_id, battery=100, color=color)
        # ログはドックパネルに表示（アクティブパネルなし）

    # ── 全機緊急停止ダイアログ ──────────────
    def all_emergency_dialog(self):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("⛔ 全機緊急停止")
        dlg.setText(
            "<b style='color:#ff4444'>全ドローンを緊急停止しますか？</b><br><br>"
            "操作を選択してください。"
        )
        dlg.setStyleSheet(
            "QMessageBox { background-color:#1a1a2e; color:#ffffff; }"
            "QLabel { color:#ffffff; font-size:13px; }"
            "QPushButton { padding:6px 14px; font-size:12px; border-radius:4px; }"
        )
        btn_return = dlg.addButton("🟡 全機母艦へ帰還", QMessageBox.ButtonRole.AcceptRole)
        btn_stop   = dlg.addButton("⛔ 全機即時停止",   QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = dlg.addButton("キャンセル",        QMessageBox.ButtonRole.RejectRole)
        btn_return.setStyleSheet("background-color:#444400; color:#ffaa00; border:1px solid #ffaa00;")
        btn_stop.setStyleSheet(  "background-color:#ff0000; color:#ffffff; border:2px solid #ffffff;")
        btn_cancel.setStyleSheet("background-color:#333333; color:#aaaaaa; border:1px solid #aaaaaa;")
        dlg.exec()

        clicked = dlg.clickedButton()
        if clicked == btn_return:
            for p in self.drone_panels:
                p.start_return_mode()
        elif clicked == btn_stop:
            for p in self.drone_panels:
                p._do_emergency_stop()

    # ── 入れ替えロジック ────────────────────
    def on_swap_needed(self, active_drone_id: int):
        """アクティブパネルからの入れ替え推奨シグナルを受け取る"""
        if self.dock.has_available_drone():
            # アクティブパネルに入れ替えボタンを表示
            for p in self.drone_panels:
                if p.drone_id == active_drone_id:
                    p.notify_swap_available()
                    break

    def deploy_standby_drone(self, standby_id: int):
        """
        ドックの「出撃」ボタン押下 → 入れ替え確認ダイアログ
        """
        # 入れ替え対象のアクティブ機を選ぶ（btn_swap が表示されているもの優先、なければ最初の1機）
        target_panel = None
        for p in self.drone_panels:
            if p.btn_swap.isVisible():
                target_panel = p
                break
        if target_panel is None and self.drone_panels:
            target_panel = self.drone_panels[0]

        if target_panel is None:
            return

        color = DRONE_COLORS[(standby_id - 1) % len(DRONE_COLORS)]

        dlg = QMessageBox(self)
        dlg.setWindowTitle("🔄 ドローン入れ替え確認")
        dlg.setText(
            f"<b style='color:#00ffff'>ドローン {target_panel.drone_id} を帰還させ、"
            f"ドローン {standby_id} を出撃させます。</b><br><br>"
            "実行してもよいですか？"
        )
        dlg.setStyleSheet(
            "QMessageBox { background-color:#1a1a2e; color:#ffffff; }"
            "QLabel { color:#ffffff; font-size:13px; }"
            "QPushButton { padding:6px 14px; font-size:12px; border-radius:4px; }"
        )
        btn_ok     = dlg.addButton("🔄 入れ替え実行", QMessageBox.ButtonRole.AcceptRole)
        btn_cancel = dlg.addButton("キャンセル",      QMessageBox.ButtonRole.RejectRole)
        btn_ok.setStyleSheet(    "background-color:#003333; color:#00ffff; border:2px solid #00ffff;")
        btn_cancel.setStyleSheet("background-color:#333333; color:#aaaaaa; border:1px solid #aaaaaa;")
        dlg.exec()

        if dlg.clickedButton() != btn_ok:
            return

        # 1. アクティブ機を帰還させてドックへ移動
        old_id    = target_panel.drone_id
        old_bat   = target_panel.battery_drone.value()
        old_color = target_panel.color
        target_panel.start_return_mode()
        target_panel.add_log(f"🔄 ドローン {standby_id} と入れ替え → 帰還開始")

        # アクティブパネルリストから削除してドックへ
        self.drone_panels.remove(target_panel)
        self.drone_count -= 1
        target_panel.setParent(None)   # レイアウトから除去

        self.dock.add_drone(old_id, battery=old_bat, color=old_color)
        self.dock.remove_drone(standby_id)

        # 2. 待機機を新しいアクティブパネルとして追加
        new_color = DRONE_COLORS[(standby_id - 1) % len(DRONE_COLORS)]
        new_panel = DronePanelWidget(drone_id=standby_id, color=new_color)
        new_panel.setMinimumWidth(670)
        new_panel.swap_needed.connect(self.on_swap_needed)

        self.drone_count += 1
        if self.drone_count > 1:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.VLine)
            sep.setStyleSheet("color:#333355;")
            self.panels_layout.insertWidget(self.panels_layout.count() - 1, sep)

        self.panels_layout.insertWidget(self.panels_layout.count() - 1, new_panel)
        self.drone_panels.append(new_panel)
        new_panel.init_log()
        new_panel.add_log(f"🔄 ドローン {old_id} と入れ替えで出撃！")
        self._update_title()

    # ── 定期更新 ────────────────────────────
    def update_all(self):
        for p in self.drone_panels:
            p.update_display()
            # バッテリー30%以下で待機機があれば入れ替え推奨
            bat = p.battery_drone.value()
            p.check_swap_needed(bat, self.dock.has_available_drone())

    def _update_title(self):
        standby = len(self.dock.standby_drones)
        self.setWindowTitle(
            f"PHENIX Command Center v3.2 — 運用:{self.drone_count}機  待機:{standby}機"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PHENIXMain()
    window.show()
    sys.exit(app.exec())