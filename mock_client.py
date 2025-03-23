import socket
import json

HOST = "127.0.0.1"  # or "127.0.0.1" if testing locally
PORT = 3000

def send_event(event):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(json.dumps(event).encode())
        response = s.recv(1024)
        print("Response:", response.decode())

# Send mock RFID
send_event({"type": "rfid", "uid": "12345678"})

# Send mock PIN
send_event({"type": "keypad", "pin": "1234"})
