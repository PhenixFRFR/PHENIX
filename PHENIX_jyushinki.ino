#include <RadioLib.h>

SX1262 radio = new Module(10, 6, 5, -1);

void setup() {
Serial.begin(115200);
Serial.println("受信機起動！");

int state = radio.begin(915.0);
if (state == RADIOLIB_ERR_NONE) {
Serial.println("SX1262 初期化成功！");
} else {
Serial.println("初期化失敗: ");
Serial.println(state);
}
}

void loop() {
String str;
int state = radio.receive(str);
if (state == RADIOLIB_ERR_NONE) {
Serial.println("受信成功！");
Serial.println(str);
} else if (state == RADIOLIB_ERR_RX_TIMEOUT) {
Serial.println("タイムアウト...");
}
}
