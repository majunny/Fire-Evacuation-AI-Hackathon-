# pico_receiver_one.py
from machine import Pin
import sys

led_pin0 = Pin(0, Pin.OUT)  # 1번 핀(GPIO0)
led_pin1 = Pin(1, Pin.OUT)
led_pin2 = Pin(2, Pin.OUT)
led_pin3 = Pin(3, Pin.OUT)
led_pin4 = Pin(4, Pin.OUT)
led_pin5 = Pin(5, Pin.OUT)

print('imready')

while True:
    line = sys.stdin.readline()  # PC에서 오는 데이터 받기
    if not line:
        continue

    line = line.strip()

    if line == "2,0_ON":  # 2차원 좌표라고 생각하면 됌요
        led_pin0.value(1)
    elif line == "2,0_OFF":
        led_pin0.value(0)

    if line == "2,1_ON":  # 2차원 좌표라고 생각하면 됌요
        led_pin1.value(1)
    elif line == "2,1_OFF":
        led_pin1.value(0)

    if line == "2,2_ON":  # 2차원 좌표라고 생각하면 됌요
        led_pin2.value(1)
    elif line == "2,2_OFF":
        led_pin2.value(0)

    if line == "2,3_ON":  # 2차원 좌표라고 생각하면 됌요
        led_pin3.value(1)
    elif line == "2,3_OFF":
        led_pin3.value(0)

    if line == "2,4_ON":  # 2차원 좌표라고 생각하면 됌요
        led_pin4.value(1)
    elif line == "2,4_OFF":
        led_pin4.value(0)

    if line == "2,5_ON":  # 2차원 좌표라고 생각하면 됌요
        led_pin5.value(1)
    elif line == "2,5_OFF":
        led_pin5.value(0)