import json
import platform
import socket
import sys
import time

import psutil
import serial
import serial.tools.list_ports

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
BAUD_RATE = 115200
UPDATE_INTERVAL = 2


def find_pico_port():
    while True:
        ports = serial.tools.list_ports.comports()
        for p in ports:
            if any(x in p.description for x in ["Pico", "Board", "USB Serial", "RP2"]):
                print(f"[*] Found Pico on {p.device}")
                return p.device
        print("[!] Waiting for Pico...")
        time.sleep(5)


def get_pc_stats():
    # Get Local IP Address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 1))
        ip_addr = s.getsockname()[0]
    except:
        ip_addr = "N/A"
    finally:
        s.close()

    return {
        "cpu_percent": psutil.cpu_percent(),
        "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
        "ram_used": psutil.virtual_memory().used,
        "ram_total": psutil.virtual_memory().total,
        "ram_pct": psutil.virtual_memory().percent,
        "hostname": socket.gethostname(),
        "ip_addr": ip_addr,
        "os": platform.system(),
        "os_version": platform.release(),  # e.g., "10" or "11"
    }


def main():
    print("--- PC Dashboard Controller ---")
    while True:
        port = find_pico_port()
        try:
            ser = serial.Serial(port, BAUD_RATE, timeout=1)
            ser.setDTR(True)
            print("[*] Port Open. Waiting for Pico boot...")
            time.sleep(2)
            ser.reset_input_buffer()

            print("[*] Handshaking...")
            ser.write(b"HELLO\n")

            response = ser.readline().decode(errors="ignore").strip()
            if response != "READY":
                ser.close()
                continue

            print("[+] Connected and Streaming.")

            while True:
                stats = get_pc_stats()
                ser.write((json.dumps(stats) + "\n").encode("utf-8"))
                ser.flush()
                time.sleep(UPDATE_INTERVAL)

        except (serial.SerialException, KeyboardInterrupt):
            print("\n[!] Connection lost or stopped.")
            break


if __name__ == "__main__":
    main()
