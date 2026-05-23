#include <RadioLib.h>

SX1262 radio = new Module(10, 6, 5, -1);

void setup() {
  Serial.begin(115200);
  Serial.println("送信機起動！");
  
  int state = radio.begin(915.0);
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println("SX1262 初期化成功！");
  } else {
    Serial.println("初期化失敗: ");
    Serial.println(state);
  }
}

void loop() {
  int state = radio.transmit("PHENIX テスト送信！");
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println("送信成功！");
  } else {
    Serial.println("送信失敗: ");
    Serial.println(state);
  }
  delay(2000);
}
