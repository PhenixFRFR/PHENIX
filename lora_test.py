import time
import random
from datetime import datetime
 
 
def simulate_lora_send(message, frequency=915.0):
    """LoRa送信シミュレーション"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 送信中: {message}")
    print(f"  周波数: {frequency} MHz")
    time.sleep(0.5)
    success = random.random() > 0.1
    if success:
        print(f"  送信成功！")
        return True
    else:
        print(f"  送信失敗")
        return False
 
 
def simulate_lora_receive(timeout=5):
    """LoRa受信シミュレーション"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 受信待機中...")
    time.sleep(random.uniform(0.5, 2.0))
    rssi = random.randint(-95, -55)
    snr = random.uniform(-5, 10)
    messages = [
        "PHENIX ノード1 正常稼働中",
        "PHENIX ノード2 正常稼働中",
        "PHENIX ノード3 正常稼働中",
        "PHENIX 母艦 GPS: 33.8688, 151.2093",
        "PHENIX ドローン 高度: 25m",
    ]
    message = random.choice(messages)
    print(f"  受信成功！")
    print(f"  メッセージ: {message}")
    print(f"  RSSI: {rssi} dBm")
    print(f"  SNR: {snr:.1f} dB")
    return message, rssi, snr
 
 
def check_rssi_threshold(rssi, threshold=-85, countdown=7):
    """RSSI閾値チェックとノード投下判定"""
    if rssi < threshold:
        print(f"  電波弱化検知！RSSI: {rssi} dBm")
        print(f"  投下カウントダウン開始: {countdown}秒")
        return True
    return False
 
 
def main():
    print("=" * 50)
    print(" PHENIX LoRa通信テスト")
    print("=" * 50)
    print()
 
    node_count = 3
    total_sent = 0
    total_success = 0
    rssi_history = []
 
    for i in range(10):
        print(f"--- テスト {i+1}/10 ---")
 
        # 送信テスト
        message = f"PHENIX テスト送信 #{i+1}"
        success = simulate_lora_send(message)
        total_sent += 1
        if success:
            total_success += 1
 
        # 受信テスト
        received, rssi, snr = simulate_lora_receive()
        rssi_history.append(rssi)
 
        # RSSI閾値チェック
        need_drop = check_rssi_threshold(rssi)
        if need_drop and node_count > 0:
            node_count -= 1
            print(f"  ノード投下！残り{node_count}個")
 
        print()
        time.sleep(1)
 
    # 結果まとめ
    print("=" * 50)
    print(" テスト結果")
    print("=" * 50)
    print(f"送信成功率: {total_success}/{total_sent} ({total_success/total_sent*100:.0f}%)")
    print(f"平均RSSI: {sum(rssi_history)/len(rssi_history):.1f} dBm")
    print(f"最大RSSI: {max(rssi_history)} dBm")
    print(f"最小RSSI: {min(rssi_history)} dBm")
    print(f"残りノード数: {node_count}個")
    print()
    print(" テスト完了！")
 
 
if __name__ == "__main__":
    main()
