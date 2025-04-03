import socket
import threading
import json
from datetime import datetime

LOG_FILE = "central_access_log.json"

def log_to_file(entry):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"[LOG] {entry}")
    except Exception as e:
        print(f"[ERROR] Failed to write log: {e}")

def handle_client(conn, addr):
    print(f"[CONNECTED] {addr}")
    try:
        data = conn.recv(4096)
        if not data:
            return
        try:
            log_entry = json.loads(data.decode("utf-8"))
            log_entry["received_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_to_file(log_entry)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON: {e}")
    finally:
        conn.close()
        print(f"[DISCONNECTED] {addr}")

def start_server(host="0.0.0.0", port=5005):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[LISTENING] GateWise TCP listener on {host}:{port}")
    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Listener stopped.")
    finally:
        server.close()
