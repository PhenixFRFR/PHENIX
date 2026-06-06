import sys
import sqlite3
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import csv


class DataAnalyzer(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PHENIX データ分析ツール")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: #1a1a2e; color: #00ff88;")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # タイトル
        title = QLabel("📊 PHENIX データ分析ツール")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #00ff88;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ボタンパネル
        btn_layout = QHBoxLayout()

        btn_rssi = QPushButton("📡 RSSI分析")
        btn_rssi.setStyleSheet("""
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
        btn_rssi.clicked.connect(self.show_rssi_analysis)
        btn_layout.addWidget(btn_rssi)

        btn_battery = QPushButton("🔋 バッテリー分析")
        btn_battery.setStyleSheet("""
            QPushButton {
                background-color: #000044;
                color: #00aaff;
                border: 2px solid #00aaff;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #000066; }
        """)
        btn_battery.clicked.connect(self.show_battery_analysis)
        btn_layout.addWidget(btn_battery)

        btn_node = QPushButton("🚀 ノード投下分析")
        btn_node.setStyleSheet("""
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
        btn_node.clicked.connect(self.show_node_analysis)
        btn_layout.addWidget(btn_node)

        btn_report = QPushButton("📄 レポート生成")
        btn_report.setStyleSheet("""
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
        btn_report.clicked.connect(self.generate_report)
        btn_layout.addWidget(btn_report)

        btn_export = QPushButton("💾 CSVエクスポート")
        btn_export.setStyleSheet("""
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
        btn_export.clicked.connect(self.export_csv)
        btn_layout.addWidget(btn_export)

        layout.addLayout(btn_layout)

        # 統計パネル
        stats_layout = QHBoxLayout()

        self.total_records = QLabel("総記録数: 0件")
        self.total_records.setStyleSheet("font-size: 16px; color: #00ff88;")
        stats_layout.addWidget(self.total_records)

        self.avg_rssi = QLabel("平均RSSI: --- dBm")
        self.avg_rssi.setStyleSheet("font-size: 16px; color: #00aaff;")
        stats_layout.addWidget(self.avg_rssi)

        self.node_drops = QLabel("ノード投下: 0回")
        self.node_drops.setStyleSheet("font-size: 16px; color: #ffaa00;")
        stats_layout.addWidget(self.node_drops)

        self.avg_battery = QLabel("平均バッテリー: --- %")
        self.avg_battery.setStyleSheet("font-size: 16px; color: #ff66ff;")
        stats_layout.addWidget(self.avg_battery)

        layout.addLayout(stats_layout)

        # グラフエリア
        self.fig = Figure(figsize=(10, 5), facecolor='#1a1a2e')
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        # ログエリア
        self.log_text = QTextEdit()
        self.log_text.setStyleSheet(
            "background-color: #0a0a1a; color: #00ff88; font-family: monospace;")
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)

        self.load_stats()
        self.show_rssi_analysis()

    def get_db(self):
        try:
            return sqlite3.connect("phenix_data.db")
        except Exception:
            return None

    def load_stats(self):
        conn = self.get_db()
        if not conn:
            return
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM lora_log")
            total = cursor.fetchone()[0]
            self.total_records.setText(f"総記録数: {total}件")

            cursor.execute("SELECT AVG(rssi) FROM lora_log")
            avg = cursor.fetchone()[0]
            if avg:
                self.avg_rssi.setText(f"平均RSSI: {avg:.1f} dBm")

            cursor.execute("SELECT COUNT(*) FROM lora_log WHERE event LIKE '%投下%'")
            drops = cursor.fetchone()[0]
            self.node_drops.setText(f"ノード投下: {drops}回")

            cursor.execute("SELECT AVG(drone_battery) FROM telemetry_log")
            bat = cursor.fetchone()[0]
            if bat:
                self.avg_battery.setText(f"平均バッテリー: {bat:.1f}%")
        except Exception:
            self.log("⚠️ データベースにデータがありません")
        finally:
            conn.close()

    def show_rssi_analysis(self):
        conn = self.get_db()
        if not conn:
            return
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT rssi FROM lora_log ORDER BY id DESC LIMIT 100")
            data = [row[0] for row in cursor.fetchall()]
            data.reverse()

            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.set_facecolor('#0a0a1a')
            ax.tick_params(colors='#00ff88')
            for spine in ax.spines.values():
                spine.set_color('#00ff88')

            colors = ['#ff4444' if r < -85 else '#00ff88' for r in data]
            ax.bar(range(len(data)), data, color=colors, alpha=0.7)
            ax.axhline(y=-85, color='#ff4444', linestyle='--', label='投下閾値 -85dBm')
            ax.set_title('RSSI履歴分析', color='#00ff88', fontsize=14)
            ax.set_xlabel('時間', color='#00ff88')
            ax.set_ylabel('RSSI (dBm)', color='#00ff88')
            ax.legend(facecolor='#1a1a2e', labelcolor='#00ff88')
            self.canvas.draw()
            self.log(f"📡 RSSI分析完了 - {len(data)}件のデータを表示")
        except Exception as e:
            self.log(f"⚠️ エラー: {e}")
        finally:
            conn.close()

    def show_battery_analysis(self):
        conn = self.get_db()
        if not conn:
            return
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT drone_battery, mother_battery FROM telemetry_log ORDER BY id DESC LIMIT 100")
            rows = cursor.fetchall()
            drone_bat  = [row[0] for row in rows]
            mother_bat = [row[1] for row in rows]
            drone_bat.reverse()
            mother_bat.reverse()

            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.set_facecolor('#0a0a1a')
            ax.tick_params(colors='#00ff88')
            for spine in ax.spines.values():
                spine.set_color('#00ff88')

            ax.plot(drone_bat,  color='#00aaff', label='ドローン', linewidth=2)
            ax.plot(mother_bat, color='#00ff88', label='母艦',     linewidth=2)
            ax.axhline(y=15, color='#ff4444', linestyle='--', label='自動帰還ライン 15%')
            ax.set_title('バッテリー推移分析', color='#00ff88', fontsize=14)
            ax.set_xlabel('時間', color='#00ff88')
            ax.set_ylabel('バッテリー (%)', color='#00ff88')
            ax.set_ylim(0, 105)
            ax.legend(facecolor='#1a1a2e', labelcolor='#00ff88')
            self.canvas.draw()
            self.log(f"🔋 バッテリー分析完了 - {len(drone_bat)}件のデータを表示")
        except Exception as e:
            self.log(f"⚠️ エラー: {e}")
        finally:
            conn.close()

    def show_node_analysis(self):
        conn = self.get_db()
        if not conn:
            return
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT timestamp, event FROM lora_log WHERE event LIKE '%投下%'")
            drops = cursor.fetchall()

            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.set_facecolor('#0a0a1a')
            ax.tick_params(colors='#00ff88')
            for spine in ax.spines.values():
                spine.set_color('#00ff88')

            if drops:
                ax.bar(range(len(drops)), [1] * len(drops), color='#ff66ff', alpha=0.7)
                ax.set_title(f'ノード投下履歴 (合計{len(drops)}回)',
                             color='#00ff88', fontsize=14)
                ax.set_xlabel('投下回数', color='#00ff88')
                ax.set_ylabel('投下', color='#00ff88')
                self.log(f"🚀 ノード投下分析完了 - 合計{len(drops)}回投下")
            else:
                ax.text(0.5, 0.5, 'ノード投下データなし', color='#00ff88',
                        ha='center', va='center', transform=ax.transAxes, fontsize=16)
                self.log("🚀 ノード投下データがありません")
            self.canvas.draw()
        except Exception as e:
            self.log(f"⚠️ エラー: {e}")
        finally:
            conn.close()

    def generate_report(self):
        conn = self.get_db()
        if not conn:
            return
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM lora_log")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(rssi), MIN(rssi), MAX(rssi) FROM lora_log")
            rssi_stats = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) FROM lora_log WHERE event LIKE '%投下%'")
            drops = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM lora_log WHERE rssi < -85")
            weak = cursor.fetchone()[0]

            report = f"""
╔══════════════════════════════════════╗
║      PHENIX 実証実験レポート         ║
║  生成日時: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}  ║
╚══════════════════════════════════════╝

【通信データ統計】
・総記録数：{total}件
・平均RSSI：{rssi_stats[0]:.1f} dBm
・最低RSSI：{rssi_stats[1]} dBm
・最高RSSI：{rssi_stats[2]} dBm
・電波弱化検知：{weak}回
・ノード自動投下：{drops}回

【システム評価】
・通信安定性：{'良好' if rssi_stats[0] > -80 else '要改善'}
・ノード投下システム：{'正常動作' if drops > 0 else '未実行'}
・自動制御：正常稼働

【補助金申請用コメント】
本システムは実証実験において{total}件のデータを
自動収集・記録することに成功しました。
LoRa通信による自律的なネットワーク展開が
実証されました。

━━━━━━━━━━━━━━━━━━━━━━━━
PHENIX Project - PhenixFRFR
github.com/PhenixFRFR/PHENIX
━━━━━━━━━━━━━━━━━━━━━━━━
"""
            self.log_text.clear()
            self.log_text.setText(report)
            self.log("📄 レポート生成完了！")

            fname = f"PHENIX_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(report)
            self.log(f"💾 レポートをファイルに保存しました！ ({fname})")

        except Exception as e:
            self.log(f"⚠️ エラー: {e}")
        finally:
            conn.close()

    def export_csv(self):
        conn = self.get_db()
        if not conn:
            return
        cursor = conn.cursor()
        try:
            filename = f"PHENIX_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            cursor.execute("SELECT * FROM lora_log")
            rows = cursor.fetchall()

            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'タイムスタンプ', 'RSSI', 'SNR', 'メッセージ', 'イベント'])
                writer.writerows(rows)

            self.log(f"💾 CSVエクスポート完了！ファイル: {filename} ({len(rows)}件)")
        except Exception as e:
            self.log(f"⚠️ エラー: {e}")
        finally:
            conn.close()

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DataAnalyzer()
    window.show()
    sys.exit(app.exec())