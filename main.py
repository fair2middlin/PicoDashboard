import sys
import uselect
import utime
import ujson
import machine
import gc
from lcd_api import LcdApi
from pico_i2c_lcd import I2cLcd

# --- Setup ---
i2c = machine.I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000)
lcd = I2cLcd(i2c, 0x27, 2, 16)

def get_pico_temp():
    sensor = machine.ADC(4)
    reading = sensor.read_u16() * 3.3 / 65535
    return 27 - (reading - 0.706) / 0.001721

# --- State ---
buffer = ""
pc_data = None
page = 0
last_pc_time = utime.ticks_ms()
last_page_time = utime.ticks_ms()
hb_toggle = False

poll = uselect.poll()
poll.register(sys.stdin, uselect.POLLIN)

lcd.clear()
lcd.putstr("PC DASHBOARD\nWaiting for link")

while True:
    # 1. Serial Listener
    if poll.poll(0):
        char = sys.stdin.read(1)
        if char == "\n":
            msg = buffer.strip()
            buffer = ""
            if msg == "HELLO":
                sys.stdout.write("READY\n")
            elif msg.startswith('{'):
                try:
                    pc_data = ujson.loads(msg)
                    last_pc_time = utime.ticks_ms()
                    hb_toggle = not hb_toggle
                    sys.stdout.write("ACK\n")
                except: pass
        else:
            buffer += char

    # 2. Display Refresh (Every 2.5s)
    if utime.ticks_diff(utime.ticks_ms(), last_page_time) > 2500:
        last_page_time = utime.ticks_ms()
        lcd.clear()
        
        # Watchdog: If no data for 10s
        if utime.ticks_diff(utime.ticks_ms(), last_pc_time) > 10000:
            lcd.putstr("PC OFFLINE")
            page = 4 
        elif pc_data:
            # Heartbeat indicator in top right
            lcd.move_to(15, 0)
            lcd.putstr("*" if hb_toggle else ".")
            lcd.move_to(0, 0)

            if page == 0: # CPU Page
                lcd.putstr(f"PC CPU: {pc_data['cpu_percent']}%")
                lcd.move_to(0, 1)
                lcd.putstr(f"Freq: {int(pc_data['cpu_freq'])}MHz")
            elif page == 1: # RAM Page
                used = pc_data['ram_used'] // 1073741824
                total = pc_data['ram_total'] // 1073741824
                lcd.putstr(f"PC RAM: {pc_data['ram_pct']}%")
                lcd.move_to(0, 1)
                lcd.putstr(f"Used: {used}/{total}GB")
            elif page == 2: # Network Page
                lcd.putstr(f"PC: {pc_data['hostname'][:12]}")
                lcd.move_to(0, 1)
                lcd.putstr(f"IP: {pc_data['ip_addr']}")
            elif page == 3: # OS Page
                lcd.putstr(f"OS: {pc_data['os']}")
                lcd.move_to(0, 1)
                lcd.putstr(f"Ver: {pc_data['os_version']}")
            elif page == 4: # Pico Stats
                lcd.putstr(f"Pico T: {get_pico_temp():.1f}C")
                lcd.move_to(0, 1)
                lcd.putstr(f"Up: {utime.ticks_ms()//1000}s")

            page = (page + 1) % 5
        
    utime.sleep_ms(10)