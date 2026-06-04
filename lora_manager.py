import time
import random
import sqlite3
from datetime import datetime
from threading import Thread
 
 
class LoRaManager:
 
    def __init__(self, db_path="phenix_data.db"):
        self.db_path = db_path
        self.running = False
        self.node_count = 3
        self.rssi_history = []
        self.countdown = 0
        self.setup_database()
 
    def setup_database(self):
        """SQLiteデータベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lora_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                rssi INTEGER,
                snr REAL,
                message TEXT,
                event TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS node_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                node_id INTEGER,
                lat REAL,
                lng REAL,
                battery INTEGER,
                status TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                mother_bat INTEGER,
                drone_bat INTEGER,
                altitude REAL,
                speed REAL,
                heading REAL,
                temp REAL,
                humidity REAL,
                pressure REAL
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ データベース初期化完了")
 
    def save_lora_data(self, rssi, snr, message, event=""):
        """LoRaデータをDBに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO lora_log (timestamp, rssi, snr, message, event)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rssi, snr, message, event))
        conn.commit()
        conn.close()
 
    def save_system_data(self, mother_bat, drone_bat, altitude, speed, heading, temp, humidity, pressure):
        """システムデータをDBに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_log
            (timestamp, mother_bat, drone_bat, altitude, speed, heading, temp, humidity, pressure)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              mother_bat, drone_bat, altitude, speed, heading, temp, humidity, pressure))
        conn.commit()
        conn.close()
 
    def check_rssi(self, rssi):
        """RSSI監視・ノード投下判定"""
        self.rssi_history.append(rssi)
        if len(self.rssi_history) > 60:
            self.rssi_history.pop(0)
 
        if rssi < -85:
            self.countdown += 1
            if self.countdown >= 7:
                if self.node_count > 0:
                    self.node_count -= 1
                    self.countdown = 0
                    event = f"ノード投下 残り{self.node_count}個"
                    print(f"🚀 {event}")
                    return event
            return f"カウントダウン: {self.countdown}秒"
        else:
            self.countdown = 0
            return ""
 
    def get_stats(self):
        """統計情報を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM lora_log")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT AVG(rssi) FROM lora_log")
        avg_rssi = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM lora_log WHERE event LIKE 'ノード%'")
        drops = cursor.fetchone()[0]
        conn.close()
        return {
            "total_records": total,
            "avg_rssi": avg_rssi,
            "node_drops": drops,
            "node_remaining": self.node_count
        }
 
    def run_simulation(self):
        """シミュレーション実行"""
        self.running = True
        print("🔥 PHENIX LoRa Manager 起動！")
        print("=" * 50)
 
        while self.running:
            rssi = random.randint(-95, -55)
            snr = random.uniform(-5, 10)
            message = f"PHENIX データ {datetime.now().strftime('%H:%M:%S')}"
 
            event = self.check_rssi(rssi)
            self.save_lora_data(rssi, snr, message, event)
 
            mother_bat = random.randint(70, 100)
            drone_bat = random.randint(60, 100)
            altitude = random.uniform(10, 50)
            speed = random.uniform(0, 30)
            heading = random.uniform(0, 360)
            temp = random.uniform(20, 35)
            humidity = random.uniform(40, 80)
            pressure = random.uniform(1010, 1020)
 
            self.save_system_data(
                mother_bat, drone_bat, altitude,
                speed, heading, temp, humidity, pressure
            )
 
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"RSSI: {rssi}dBm | "
                  f"ノード残: {self.node_count}個 | "
                  f"{event}")
 
            time.sleep(1)
 
    def stop(self):
        self.running = False
        stats = self.get_stats()
        print("\n" + "=" * 50)
        print("📊 最終統計")
        print(f"総記録数: {stats['total_records']}")
        print(f"平均RSSI: {stats['avg_rssi']:.1f} dBm")
        print(f"ノード投下回数: {stats['node_drops']}")
        print(f"残りノード: {stats['node_remaining']}個")
 
 
if __name__ == "__main__":
    manager = LoRaManager()
    try:
        manager.run_simulation()
    except KeyboardInterrupt:
        manager.stop()
        print("✅ 終了しました")
