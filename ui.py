import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from PIL import Image, ImageTk
import subprocess
import threading
import cv2
import os

from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO

from storage import (
    log_access, load_users, load_config,
    save_config, load_logs, export_logs_to_csv,
    is_blackout
)

# Globals
theme = {"bg": "#222", "fg": "#fff", "accent": "#444"}
is_minimized = False
users = load_users()
config = load_config()


def load_and_resize_image(path, size):
    img = Image.open(path)
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def make_label_button(parent, text, command, image=None):
    lbl = tk.Label(parent, text=text, image=image, font=("Arial", 14),
                   fg=theme["fg"], bg=theme["bg"], cursor="hand2",
                   padx=10, pady=10, compound="top", width=90)
    lbl.bind("<Button-1>", lambda e: command())
    lbl.pack(side="left", padx=10, pady=10)
    return lbl


def run_ui():
    global theme, users, config

    root = tk.Tk()
    root.title("GateWise Access Control")
    root.geometry("1024x600")
    root.attributes("-fullscreen", True)
    root.configure(bg=theme["bg"])

    icons = {
        "feed": load_and_resize_image("assets/icons/live_feed_white.png", (80, 80)),
        "logs": load_and_resize_image("assets/icons/logs-white.png", (80, 80)),
        "config": load_and_resize_image("assets/icons/config_white.png", (80, 80)),
        "hardware": load_and_resize_image("assets/icons/hardware_white.png", (80, 80)),
        "admin": load_and_resize_image("assets/icons/admin_white.png", (80, 80)),
        "camera": load_and_resize_image("assets/icons/camera_white.png", (80, 80)),
        "rfid": load_and_resize_image("assets/icons/scan_white.png", (80, 80)),
        "back": load_and_resize_image("assets/icons/back_white.png", (50, 50)),
        "logo": load_and_resize_image("assets/icons/Gatewise.PNG", (100, 100)),
    }

    frames = {}
    for name in ["home", "feed", "hardware"]:
        frame = tk.Frame(root, bg=theme["bg"])
        frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=1, relheight=1)
        frames[name] = frame

        clock = tk.Label(frame, font=("Arial", 16), fg=theme["fg"], bg=theme["bg"])
        clock.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

        def update_clock(lbl=clock):
            lbl.config(text=datetime.now().strftime("%m-%d-%Y %H:%M"))
            lbl.after(1000, lambda: update_clock(lbl))
        update_clock()

    def show_frame(f):
        f.tkraise()

    # Home screen
    home = frames["home"]
    tk.Label(home, image=icons["logo"], bg=theme["bg"]).pack(pady=20)

    icon_frame = tk.Frame(home, bg=theme["bg"])
    icon_frame.pack(pady=30)

    buttons = [
        ("Live Feed", lambda: show_frame(frames["feed"]), icons["feed"]),
        ("Logs", lambda: print("Not implemented"), icons["logs"]),
        ("Config", lambda: print("Not implemented"), icons["config"]),
        ("Hardware", lambda: show_frame(frames["hardware"]), icons["hardware"]),
        ("Admin", lambda: print("Not implemented"), icons["admin"]),
    ]

    for i, (label, cmd, icon) in enumerate(buttons):
        cell = tk.Frame(icon_frame, bg=theme["bg"])
        cell.grid(row=i // 3, column=i % 3, padx=40, pady=20)
        make_label_button(cell, label, cmd, image=icon)

    # Feed screen
    feed = frames["feed"]
    tk.Label(feed, text="Live Feed", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=10)

    cam_label = tk.Label(feed, bg="black")
    cam_label.pack()

    def update_feed():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Camera", "Could not open camera.")
            return

        def loop():
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(cv2image)
                imgtk = ImageTk.PhotoImage(image=img.resize((800, 480)))
                cam_label.imgtk = imgtk
                cam_label.configure(image=imgtk)
                cam_label.after(10, loop)
                break

        loop()

    update_feed()

    make_label_button(feed, "", lambda: show_frame(home), icons["back"]).place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    # Hardware Test
    hardware = frames["hardware"]
    tk.Label(hardware, text="Hardware Test", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=20)

    status_var = tk.StringVar(value="Status: Awaiting test")
    tk.Label(hardware, textvariable=status_var, font=("Arial", 14), bg=theme["bg"], fg=theme["fg"]).pack(pady=10)

    def update_status(msg):
        status_var.set(f"Status: {msg}")

    def test_rfid_with_camera():
        def inner():
            try:
                update_status("Waiting for card...")
                reader = SimpleMFRC522()
                uid, _ = reader.read()
                update_status(f"Card detected: {uid}")
                GPIO.cleanup()

                # Take photo
                cap = cv2.VideoCapture(0)
                ret, frame = cap.read()
                if not ret:
                    update_status("Camera failed")
                    return
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                photo_path = f"snapshots/{uid}_{timestamp}.jpg"
                os.makedirs("snapshots", exist_ok=True)
                cv2.imwrite(photo_path, frame)
                cap.release()

                name = users.get(str(uid), {}).get("name", "Unknown")
                status = "granted" if str(uid) in users else "denied"
                if is_blackout(config) and not users.get(str(uid), {}).get("admin", False):
                    status = "denied (blackout)"
                log_access(str(uid), name, status, photo_path)
                update_status(f"{name} ({uid}): {status}")
            except Exception as e:
                update_status(f"RFID error: {e}")
                GPIO.cleanup()

        threading.Thread(target=inner).start()

    btn_frame = tk.Frame(hardware, bg=theme["bg"])
    btn_frame.pack(pady=20)
    make_label_button(btn_frame, "RFID + Camera", test_rfid_with_camera, icons["rfid"])
    make_label_button(hardware, "", lambda: show_frame(home), icons["back"]).place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    show_frame(home)
    root.mainloop()


if __name__ == "__main__":
    run_ui()
