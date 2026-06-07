import threading
import random
import json
import math
from datetime import datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# シミュレーションデータ
class PHENIXData:
    def __init__(self):
        self.drone_battery = 100
        self.mother_battery = 100
        self.rssi = -70
        self.node_count = 8
        self.nodes_deployed = 0
        self.survivors_detected = 0
        self.drone_lat = -33.2833
        self.drone_lng = 149.1000
        self.mother_lat = -33.2833
        self.mother_lng = 149.1000
        self.mode = "追従モード"
        self.altitude = 30
        self.speed = 15
        self.heading = 180
        self.temperature = 25
        self.humidity = 60
        self.nodes = []
        self.update_count = 0

    def update(self):
        self.update_count += 1
        self.drone_battery = max(0, self.drone_battery - random.uniform(0.1, 0.5))
        self.mother_battery = max(0, self.mother_battery - random.uniform(0.05, 0.2))
        self.rssi = random.randint(-95, -55)
        self.drone_lat += random.uniform(-0.0001, 0.0001)
        self.drone_lng += random.uniform(-0.0001, 0.0001)
        self.mother_lng += random.uniform(0, 0.0001)
        self.altitude = random.uniform(25, 50)
        self.speed = random.uniform(5, 30)
        self.heading = (self.heading + random.uniform(-5, 5)) % 360
        self.temperature = random.uniform(20, 35)
        self.humidity = random.uniform(40, 80)

        if self.drone_battery <= 0:
            self.drone_battery = 100

        if self.rssi < -85 and self.nodes_deployed < self.node_count:
            if random.random() < 0.05:
                self.nodes_deployed += 1
                self.nodes.append({
                    'id': self.nodes_deployed,
                    'lat': self.mother_lat + random.uniform(-0.002, 0.002),
                    'lng': self.mother_lng + random.uniform(-0.002, 0.002),
                    'rssi': random.randint(-80, -60)
                })

        if random.random() < 0.02:
            self.survivors_detected = random.randint(0, 3)


data = PHENIXData()


def update_loop():
    import time
    while True:
        data.update()
        time.sleep(1)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 PHENIX ダッシュボード</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a1a;
            color: #00ff88;
            font-family: 'Courier New', monospace;
            min-height: 100vh;
        }
        .header {
            background: #111122;
            padding: 15px 20px;
            border-bottom: 2px solid #00ff88;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            font-size: 24px;
            color: #00ff88;
        }
        .header .time {
            font-size: 14px;
            color: #666666;
        }
        .status-bar {
            background: #0a1a0a;
            padding: 8px 20px;
            border-bottom: 1px solid #003300;
            font-size: 12px;
            color: #00aaff;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            padding: 15px;
        }
        .card {
            background: #111122;
            border: 1px solid #222244;
            border-radius: 10px;
            padding: 15px;
        }
        .card h3 {
            font-size: 14px;
            color: #666666;
            margin-bottom: 10px;
            border-bottom: 1px solid #222244;
            padding-bottom: 5px;
        }
        .big-number {
            font-size: 36px;
            font-weight: bold;
            color: #00ff88;
        }
        .label {
            font-size: 12px;
            color: #666666;
            margin-top: 3px;
        }
        .progress-bar {
            width: 100%;
            height: 10px;
            background: #222244;
            border-radius: 5px;
            margin: 5px 0;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            border-radius: 5px;
            transition: width 0.5s ease;
        }
        .green { color: #00ff88; }
        .blue { color: #00aaff; }
        .orange { color: #ffaa00; }
        .red { color: #ff4444; }
        .purple { color: #ff66ff; }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .stat-item {
            background: #0a0a1a;
            border-radius: 5px;
            padding: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 22px;
            font-weight: bold;
        }
        .stat-label {
            font-size: 11px;
            color: #666666;
        }
        .alert-box {
            background: #1a0a0a;
            border: 1px solid #ff4444;
            border-radius: 5px;
            padding: 10px;
            margin: 5px 0;
            font-size: 13px;
        }
        .alert-ok {
            background: #0a1a0a;
            border-color: #00ff88;
        }
        .node-item {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #222244;
            font-size: 12px;
        }
        .map-placeholder {
            background: #0a0a1a;
            border: 1px solid #333333;
            border-radius: 5px;
            height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            color: #444444;
        }
        .coords {
            font-size: 11px;
            color: #00aaff;
            margin-top: 5px;
        }
        .mode-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
            background: #003300;
            color: #00ff88;
            border: 1px solid #00ff88;
        }
        @media (max-width: 600px) {
            .grid { grid-template-columns: 1fr; }
            .header h1 { font-size: 18px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 PHENIX ダッシュボード</h1>
        <div class="time" id="current-time">--:--:--</div>
    </div>
    <div class="status-bar" id="status-bar">
        🔗 接続中... | 📡 LoRa: 待機中 | 🛰️ GPS: 取得中
    </div>

    <div class="grid">

        <!-- フライトモード -->
        <div class="card">
            <h3>✈️ フライトステータス</h3>
            <div style="text-align:center; margin: 10px 0;">
                <span class="mode-badge" id="flight-mode">追従モード</span>
            </div>
            <div class="grid-2" style="margin-top:10px;">
                <div class="stat-item">
                    <div class="stat-value blue" id="altitude">30</div>
                    <div class="stat-label">高度 (m)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value green" id="speed">15</div>
                    <div class="stat-label">速度 (km/h)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value purple" id="heading">180</div>
                    <div class="stat-label">方位 (°)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value orange" id="rssi">-70</div>
                    <div class="stat-label">RSSI (dBm)</div>
                </div>
            </div>
        </div>

        <!-- バッテリー -->
        <div class="card">
            <h3>🔋 バッテリー</h3>
            <div style="margin: 10px 0;">
                <div style="display:flex; justify-content:space-between;">
                    <span class="blue">ドローン</span>
                    <span class="blue" id="drone-bat-label">100%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="drone-bat-bar"
                         style="width:100%; background:#00aaff;"></div>
                </div>
            </div>
            <div style="margin: 10px 0;">
                <div style="display:flex; justify-content:space-between;">
                    <span class="green">母艦</span>
                    <span class="green" id="mother-bat-label">100%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="mother-bat-bar"
                         style="width:100%; background:#00ff88;"></div>
                </div>
            </div>
            <div style="margin-top:10px;">
                <div style="display:flex; justify-content:space-between; font-size:12px;">
                    <span>ノード残数</span>
                    <span class="orange" id="node-count">8個</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-top:5px;">
                    <span>投下済み</span>
                    <span class="purple" id="nodes-deployed">0個</span>
                </div>
            </div>
        </div>

        <!-- GPS位置 -->
        <div class="card">
            <h3>📍 GPS位置情報</h3>
            <div style="margin: 5px 0;">
                <div class="label">ドローン</div>
                <div class="coords" id="drone-coords">-33.2833, 149.1000</div>
            </div>
            <div style="margin: 5px 0;">
                <div class="label">母艦</div>
                <div class="coords" id="mother-coords">-33.2833, 149.1000</div>
            </div>
            <div class="map-placeholder" style="height:120px; margin-top:10px;">
                <div>🗺️</div>
                <div style="font-size:11px; margin-top:5px;">オレンジ, NSW, Australia</div>
                <div style="font-size:10px; margin-top:3px;" id="map-info">--</div>
            </div>
        </div>

        <!-- センサー -->
        <div class="card">
            <h3>🌡️ 環境センサー</h3>
            <div class="grid-2">
                <div class="stat-item">
                    <div class="stat-value red" id="temperature">25.0</div>
                    <div class="stat-label">気温 (℃)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value blue" id="humidity">60</div>
                    <div class="stat-label">湿度 (%)</div>
                </div>
            </div>
        </div>

        <!-- 生存者検知 -->
        <div class="card">
            <h3>👤 生存者検知</h3>
            <div style="text-align:center;">
                <div class="big-number red" id="survivors">0</div>
                <div class="label">検知数</div>
            </div>
            <div id="survivor-alert" class="alert-box alert-ok" style="margin-top:10px;">
                ✅ 異常なし
            </div>
        </div>

        <!-- アラート -->
        <div class="card">
            <h3>⚠️ システムアラート</h3>
            <div id="alerts-container">
                <div class="alert-box alert-ok">✅ 全システム正常稼働中</div>
            </div>
        </div>

        <!-- ノードネットワーク -->
        <div class="card" style="grid-column: span 2;">
            <h3>📡 ノードネットワーク</h3>
            <div id="nodes-container">
                <div style="color:#444444; font-size:12px;">ノード投下待機中...</div>
            </div>
        </div>

    </div>

    <script>
        function updateTime() {
            const now = new Date();
            document.getElementById('current-time').textContent =
                now.toLocaleTimeString('ja-JP');
        }
        setInterval(updateTime, 1000);
        updateTime();

        function updateDashboard() {
            fetch('/api/data')
                .then(r => r.json())
                .then(d => {
                    // バッテリー
                    const dbat = Math.round(d.drone_battery);
                    const mbat = Math.round(d.mother_battery);
                    document.getElementById('drone-bat-label').textContent = dbat + '%';
                    document.getElementById('mother-bat-label').textContent = mbat + '%';
                    document.getElementById('drone-bat-bar').style.width = dbat + '%';
                    document.getElementById('mother-bat-bar').style.width = mbat + '%';

                    const dbatBar = document.getElementById('drone-bat-bar');
                    dbatBar.style.background = dbat < 15 ? '#ff4444' : dbat < 30 ? '#ffaa00' : '#00aaff';

                    // フライト情報
                    document.getElementById('altitude').textContent = Math.round(d.altitude);
                    document.getElementById('speed').textContent = Math.round(d.speed);
                    document.getElementById('heading').textContent = Math.round(d.heading) + '°';
                    document.getElementById('rssi').textContent = d.rssi;

                    const rssiEl = document.getElementById('rssi');
                    rssiEl.style.color = d.rssi < -85 ? '#ff4444' : '#00ff88';

                    // GPS
                    document.getElementById('drone-coords').textContent =
                        d.drone_lat.toFixed(4) + ', ' + d.drone_lng.toFixed(4);
                    document.getElementById('mother-coords').textContent =
                        d.mother_lat.toFixed(4) + ', ' + d.mother_lng.toFixed(4);

                    // センサー
                    document.getElementById('temperature').textContent = d.temperature.toFixed(1);
                    document.getElementById('humidity').textContent = Math.round(d.humidity);

                    // ノード
                    document.getElementById('node-count').textContent =
                        (d.node_count - d.nodes_deployed) + '個';
                    document.getElementById('nodes-deployed').textContent =
                        d.nodes_deployed + '個';

                    // 生存者
                    document.getElementById('survivors').textContent = d.survivors_detected;
                    const survivorAlert = document.getElementById('survivor-alert');
                    if (d.survivors_detected > 0) {
                        survivorAlert.className = 'alert-box';
                        survivorAlert.textContent = '⚠️ 生存者' + d.survivors_detected + '人検知！';
                    } else {
                        survivorAlert.className = 'alert-box alert-ok';
                        survivorAlert.textContent = '✅ 異常なし';
                    }

                    // アラート
                    const alerts = [];
                    if (d.drone_battery < 15)
                        alerts.push('🔴 ドローンバッテリー低下！帰還してください');
                    if (d.rssi < -85)
                        alerts.push('⚠️ RSSI低下！ノード投下を検討');
                    if (d.survivors_detected > 0)
                        alerts.push('👤 生存者' + d.survivors_detected + '人検知！');

                    const alertsEl = document.getElementById('alerts-container');
                    if (alerts.length > 0) {
                        alertsEl.innerHTML = alerts.map(a =>
                            '<div class="alert-box">' + a + '</div>'
                        ).join('');
                    } else {
                        alertsEl.innerHTML = '<div class="alert-box alert-ok">✅ 全システム正常稼働中</div>';
                    }

                    // ノードネットワーク
                    const nodesEl = document.getElementById('nodes-container');
                    if (d.nodes.length > 0) {
                        nodesEl.innerHTML = d.nodes.map(n =>
                            '<div class="node-item">' +
                            '<span>📡 ノード' + n.id + '</span>' +
                            '<span style="color:#ffaa00">RSSI: ' + n.rssi + 'dBm</span>' +
                            '<span style="color:#00aaff">' + n.lat.toFixed(4) + ', ' + n.lng.toFixed(4) + '</span>' +
                            '</div>'
                        ).join('');
                    }

                    // ステータスバー
                    document.getElementById('status-bar').textContent =
                        '🔗 接続中 | 📡 RSSI: ' + d.rssi + 'dBm | ' +
                        '🔋 ドローン: ' + Math.round(d.drone_battery) + '% | ' +
                        '📡 ノード: ' + d.nodes_deployed + '/' + d.node_count + ' | ' +
                        '⏱️ 更新: ' + d.update_count + '回';
                });
        }

        setInterval(updateDashboard, 1000);
        updateDashboard();
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/data')
def api_data():
    return jsonify({
        'drone_battery': data.drone_battery,
        'mother_battery': data.mother_battery,
        'rssi': data.rssi,
        'node_count': data.node_count,
        'nodes_deployed': data.nodes_deployed,
        'survivors_detected': data.survivors_detected,
        'drone_lat': data.drone_lat,
        'drone_lng': data.drone_lng,
        'mother_lat': data.mother_lat,
        'mother_lng': data.mother_lng,
        'mode': data.mode,
        'altitude': data.altitude,
        'speed': data.speed,
        'heading': data.heading,
        'temperature': data.temperature,
        'humidity': data.humidity,
        'nodes': data.nodes,
        'update_count': data.update_count,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })


if __name__ == '__main__':
    update_thread = threading.Thread(target=update_loop, daemon=True)
    update_thread.start()

    print("🔥 PHENIX ウェブダッシュボード起動！")
    print("📱 スマホから: http://PCのIPアドレス:5000")
    print("💻 PC から:   http://localhost:5000")
    print("終了: Ctrl+C")

    app.run(host='0.0.0.0', port=5000, debug=False)