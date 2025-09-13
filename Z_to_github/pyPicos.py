# pc_controller_two.py
import serial
import time
import random

# 두 개 Pico 포트 번호 (윈도우: COM3, COM4 / 리눅스: /dev/ttyUSB0, /dev/ttyUSB1)
PICO_PORTS = ["COM3", "COM4"]

# 피코 연결 함수
def connect_picos(ports):
    return [serial.Serial(port, 115200, timeout=1) for port in ports]

# 명령어 전송 함수 (2개 피코에 동시에 전송)
def send_command(picos, command: str):
    for pico in picos:
        pico.write((command + "\n").encode())

# LED 켜기
def pico_on(picos):
    send_command(picos, "LED_ON")

# LED 끄기
def pico_off(picos):
    send_command(picos, "LED_OFF")

# 메인 실행
def main():
    picos = connect_picos(PICO_PORTS)
    time.sleep(0.5)  # 연결 안정화

    # 랜덤 테스트
    for _ in range(10):
        h = random.randint(1, 100)
        print("랜덤 값:", h)

        if h > 30:
            pico_on(picos)
            print(" → 두 Pico LED 켜짐")
        else:
            pico_off(picos)
            print(" → 두 Pico LED 꺼짐")

        time.sleep(1)

    # 연결 닫기
    for pico in picos:
        pico.close()

if __name__ == "__main__":
    main()
