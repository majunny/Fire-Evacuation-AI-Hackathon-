# pc_controller_one.py
import serial
import time
import random
import serial

# Pico 포트 (윈도우: "COM3" / 리눅스랑 맥: "/dev/ttyUSB0")
PICO_PORT = "COM4"

#picos = connect_picos(PICO_PORTS)

# 피코 연결 함수
def connect_pico(port):
    return serial.Serial(port, 115200, timeout=1)

print('h')

# 명령어 전송 함수
def send_command(pico, command: str):
    pico.write((command + "\n").encode())

print('h')

# 메인 실행
def picoon():
    pico = connect_pico(PICO_PORT)
    time.sleep(0.5)  # 연결 안정화

    send_command(pico, "LED_ON")

def picooff():
    pico = connect_pico(PICO_PORT)
    time.sleep(0.5)

    send_command(pico, "LED_OFF")


print('h')

h = random.randint(1, 100)

while h > 0:
    h = random.randint(1, 100)

    if h > 30:
        picoon()
    else:
        picooff()

