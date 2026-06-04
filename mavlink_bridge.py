import time
import random
from datetime import datetime
from threading import Thread
import sqlite3


class MAVLinkBridge:

    def __init__(self, db_path="phenix_data.db"):
        self.db_path = db_path
        self.running = False
        self.connected = False
        self.drone_data = {
            "lat": 0.0,
            "lng": 0.0,
            "altitude": 0.0,
            "speed": 0.0,
            "heading": 0.0,
            "battery": 100,
            "mode": "STABILIZE",
            "armed": False,
            "rssi": -70,
            "satellites": 8
        }
        self.mother_data = {
            "lat": 0.0,
            "lng": 0.0,
            "speed": 0.0,
            "heading": 0.0,
            "battery": 100
        }

    def connect(self, connection_string="udp:127.0.0.1:14550"):
        """MAVLink接続（シミュレーション）"""
        print(f"✅ MAVLink接続中: {connection_string}")
        time.sleep(1)
        self.connected = True
        print("✅ MAVLink接続成功！")
        return True

    def get_drone_telemetry(self):
        """ドローンテレメトリーデータ取得"""
        if not self.connected:
            return None
        self.drone_data["lat"] = -33.8688 + random.uniform(-0.001, 0.001)
        self.drone_data["lng"] = 151.2093 + random.uniform(-0.001, 0.001)
        self.drone_data["altitude"] = random.uniform(10, 50)
        self.drone_data["speed"] = random.uniform(0, 30)
        self.drone_data["heading"] = random.uniform(0, 360)
        self.drone_data["battery"] = random.randint(60, 100)
        self.drone_data["rssi"] = random.randint(-95, -55)
        self.drone_data["satellites"] = random.randint(6, 12)
        return self.drone_data

    def get_mother_telemetry(self):
        """母艦テレメトリーデータ取得"""
        if not self.connected:
            return None
        self.mother_data["lat"] = -33.8688 + random.uniform(-0.002, 0.002)
        self.mother_data["lng"] = 151.2093 + random.uniform(-0.002, 0.002)
        self.mother_data["speed"] = random.uniform(0, 20)
        self.mother_data["heading"] = random.uniform(0, 360)
        self.mother_data["battery"] = random.randint(70, 100)
        return self.mother_data

    def send_command(self, command, params={}):
        """MAVLinkコマンド送信"""
        print(f"📡 コマンド送信: {command} {params}")
        time.sleep(0.1)
        print(f"✅ コマンド実行完了: {command}")
        return True

    def set_mode(self, mode):
        """飛行モード変更"""
        modes = ["STABILIZE", "LOITER", "AUTO", "GUIDED", "FOLLOW"]
        if mode in modes:
            self.drone_data["mode"] = mode
            print(f"✅ モード変更: {mode}")
            return True
        return False

    def arm(self):
        """アーム"""
        self.drone_data["armed"] = True
        print("✅ アーム完了！")
        return True

    def disarm(self):
        """ディスアーム"""
        self.drone_data["armed"] = False
        print("✅ ディスアーム完了！")
        return True

    def save_telemetry(self, drone_data, mother_data):
        """テレメトリーデータをDBに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telemetry_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                drone_lat REAL,
                drone_lng REAL,
                drone_alt REAL,
                drone_speed REAL,
                drone_heading REAL,
                drone_battery INTEGER,
                drone_mode TEXT,
                mother_lat REAL,
                mother_lng REAL,
                mother_speed REAL,
                mother_battery INTEGER
            )
        ''')
        cursor.execute('''
            INSERT INTO telemetry_log
            VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            drone_data["lat"], drone_data["lng"],
            drone_data["altitude"], drone_data["speed"],
            drone_data["heading"], drone_data["battery"],
            drone_data["mode"],
            mother_data["lat"], mother_data["lng"],
            mother_data["speed"], mother_data["battery"]
        ))
        conn.commit()
        conn.close()

    def run(self):
        """メインループ"""
        self.running = True
        self.connect()
        print("\n🔥 PHENIX MAVLink Bridge 起動！")
        print("=" * 50)

        while self.running:
            drone = self.get_drone_telemetry()
            mother = self.get_mother_telemetry()
            if drone and mother:
                self.save_telemetry(drone, mother)
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"ドローン: {drone['altitude']:.1f}m | "
                    f"速度: {drone['speed']:.1f}km/h | "
                    f"バッテリー: {drone['battery']}% | "
                    f"モード: {drone['mode']}"
                )
            time.sleep(1)

    def stop(self):
        self.running = False
        print("✅ MAVLink Bridge 停止")


if __name__ == "__main__":
    bridge = MAVLinkBridge()
    try:
        bridge.run()
    except KeyboardInterrupt:
        bridge.stop()