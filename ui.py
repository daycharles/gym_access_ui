import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from PIL import Image, ImageTk
import subprocess
import cv2
import os
from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO
from threading import Thread
from camera import get_mock_frame, take_mock_snapshot, take_snapshot
from storage import (
    log_access, load_users, load_config,
    save_config, load_logs, export_logs_to_csv,
    is_blackout
)
from wifi import load_wifi_config, save_wifi_config, write_to_wpa_supplicant, restart_wifi
import os

# Theme Definitions
DAY_THEME = {"bg": "#ffffff", "fg": "#000000", "accent": "#dddddd", "button": "#f0f0f0"}
NIGHT_THEME = {"bg": "#294856", "fg": "#ffffff", "accent": "#3a3a3a", "button": "#2d2d2d"}
# TODO: Add more themes (branding?) Include logo in the theme?

theme_mode = None
theme = {}
is_minimized = False
camera = cv2.VideoCapture(0)
reader = SimpleMFRC522()
users = load_users()
config = load_config()


def determine_theme(mode):
    hour = datetime.now().hour
    if mode == "day":
        return DAY_THEME
    elif mode == "night":
        return NIGHT_THEME
    elif mode == "system":
        return DAY_THEME if 7 <= hour < 19 else NIGHT_THEME
    return DAY_THEME

def play_beep():
    os.system('beep -f 1000 -l 200')

def reload_theme(root, frames, configuration):
    global theme, theme_mode
    theme_mode = configuration.get("theme_mode", "system")
    theme = determine_theme(theme_mode)

    # Apply to root
    root.configure(bg=theme["bg"])

    # Update all frames
    for frame in frames.values():
        frame.configure(bg=theme["bg"])
        for widget in frame.winfo_children():
            try:
                widget.configure(bg=theme["bg"], fg=theme["fg"])
            except:
                pass

SNAPSHOT_DIR = "snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

def start_live_detection():
    def reader_loop():
        detection_reader = SimpleMFRC522()
        user = load_users()

        while True:
            try:
                uid, _ = detection_reader.read()
                uid = str(uid)
                user = user.get(uid)
                name = user["name"] if user else "Unknown"
                is_admin = user["admin"] if user else False

                access_granted = uid in user
                if is_blackout(load_config()) and not is_admin:
                    access_granted = False
                    status = "denied (blackout)"
                else:
                    status = "granted" if access_granted else "denied"

                snapshot = take_snapshot(uid)
                log_access(uid, name, status, snapshot)

                # Show result
                message = f"UID: {uid}\nName: {name}\nAccess: {status}"
                print(message)
                messagebox.showinfo("Access Result", message)

            except Exception as e:
                print("RFID error:", e)
            finally:
                GPIO.cleanup()

    thread = Thread(target=reader_loop, daemon=True)
    thread.start()


def snapshot_and_log(uid):
    name = users.get(uid, {}).get("name", "Unknown")
    status = "granted" if uid in users else "denied"
    if is_blackout(config) and not users.get(uid, {}).get("admin", False):
        status = "denied (blackout)"

    play_beep()

    ret, frame = camera.read()
    if ret:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshots/{uid}_{status}_{ts}.jpg"
        os.makedirs("snapshots", exist_ok=True)
        cv2.imwrite(filename, frame)
        log_access(uid, name, status, filename)
    else:
        log_access(uid, name, "camera failed", None)

    return name, status


def rfid_listener(label):
    while True:
        try:
            uid, _ = reader.read()
            name, status = snapshot_and_log(str(uid))
            label.config(text=f"Scanned UID: {uid}\nName: {name}\nStatus: {status}")
        except Efpxception as e:
            label.config(text=f"RFID Error: {e}")
        finally:
            GPIO.cleanup()

def load_and_resize_image(path, size):
    img = Image.open(path)
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def launch_keyboard(widget=None):
    subprocess.Popen(["matchbox-keyboard"])


def make_label_button(parent, text, command, image=None):
    lbl = tk.Label(parent, text=text, image=image, font=("Arial", 16),  # Increased font size to 16
                   fg=theme["fg"], bg=theme["bg"], cursor="hand2", padx=10, pady=10, compound="top", width=90)
    lbl.bind("<Button-1>", lambda e: command())
    lbl.bind("<Enter>", lambda e: lbl.config(bg=theme["accent"]))
    lbl.bind("<Leave>", lambda e: lbl.config(bg=theme["bg"]))
    lbl.pack(side="left", padx=10, pady=10)
    return lbl


def run_ui():
    global theme, theme_mode
    config = load_config()
    theme_mode = config.get("theme_mode", "system")
    theme = determine_theme(theme_mode)

    root = tk.Tk()
    root.title("GateWise Access Control")
    root.geometry("1024x600")
    root.attributes("-fullscreen", True)
    root.configure(bg=theme["bg"])

    video_frame = tk.Label(root, bg="black")
    video_frame.pack(pady=10)

    scan_result = tk.Label(root, text="Waiting for scan...", font=("Arial", 18), bg=theme["bg"], fg=theme["fg"])
    scan_result.pack(pady=10)

    def update_frame():
        ret, frame = camera.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img = img.resize((800, 480), Image.LANCZOS)
            imgtk = ImageTk.PhotoImage(image=img)
            video_frame.imgtk = imgtk
            video_frame.config(image=imgtk)

        root.after(33, update_frame)


    # Load Icons
    icons = {
        "feed": load_and_resize_image("assets/icons/live_feed_white.png", (80, 80)),
        "logs": load_and_resize_image("assets/icons/logs-white.png", (80, 80)),
        "config": load_and_resize_image("assets/icons/config_white.png", (80, 80)),
        "wifi": load_and_resize_image("assets/icons/wifi_white.png", (80, 80)),
        "keypad": load_and_resize_image("assets/icons/keypad_white.png", (80, 80)),
        "camera": load_and_resize_image("assets/icons/camera_white.png", (80, 80)),
        "relay": load_and_resize_image("assets/icons/relay_white.png", (80, 80)),
        "scan": load_and_resize_image("assets/icons/scan_white.png", (80, 80)),
        "led": load_and_resize_image("assets/icons/led_white.png", (80, 80)),
        "hardware": load_and_resize_image("assets/icons/hardware_white.png", (80, 80)),
        "admin": load_and_resize_image("assets/icons/admin_white.png", (80, 80)),
        "minimize": load_and_resize_image("assets/icons/minimize_white.png", (80, 80)),
        "maximize": load_and_resize_image("assets/icons/maximize_white.png", (80, 80)),
        "refresh": load_and_resize_image("assets/icons/refresh_white.png", (50, 50)),
        "export": load_and_resize_image("assets/icons/export_white.png", (50, 50)),
        "save": load_and_resize_image("assets/icons/save_white.png", (50, 50)),
        "back": load_and_resize_image("assets/icons/back_white.png", (50, 50)),
        "logo": load_and_resize_image("assets/icons/Gatewise.PNG", (100, 100)),
        "rfid": load_and_resize_image("assets/icons/scan_white.png", (100, 100)),
    }

    # Page container
    frames = {}
    for name in ["home", "feed", "logs", "config", "admin", "hardware"]:
        frame = tk.Frame(root, bg=theme["bg"])
        frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=1, relheight=1)
        frames[name] = frame

        # Clock
        clock_label = tk.Label(frame, font=("Arial", 20), fg=theme["fg"], bg=theme["bg"])
        clock_label.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

        def update_clock(lbl=clock_label):
            lbl.config(text=datetime.now().strftime("%m-%d-%Y %H:%M"))
            lbl.after(1000, lambda: update_clock(lbl))

        update_clock()

    def show_frame(f):
        f.tkraise()

    def minimize_app():
        global is_minimized
        root.attributes("-fullscreen", False)
        root.iconify()
        is_minimized = True
        minimize_btn.config(image=icons["maximize"], text="Maximize")

    def maximize_app():
        global is_minimized
        root.deiconify()
        root.attributes("-fullscreen", True)
        is_minimized = False
        minimize_btn.config(image=icons["minimize"], text="Minimize")

    def toggle_minimize_maximize():
        if is_minimized:
            maximize_app()
        else:
            minimize_app()

    def simulate_scan(uid="12345678"):
        frame_img = get_mock_frame()
        snapshot_path = take_snapshot(uid)
        status = "granted" if uid in users else "denied"
        name = users.get(uid, {}).get("name", "Unknown")
        if is_blackout(config) and not users.get(uid, {}).get("admin", False):
            status = "denied (blackout)"
        log_access(uid, name, status, snapshot_path)
        messagebox.showinfo("Scan Result", f"UID: {uid}\nName: {name}\nAccess: {status}")

    # Home screen
    home = frames["home"]
    tk.Label(home, image=icons["logo"], bg=theme["bg"]).pack(pady=20)

    icon_frame = tk.Frame(home, bg=theme["bg"])
    icon_frame.pack(pady=30)

    home_buttons = [
        ("Live Feed", lambda: show_frame(frames["feed"]), icons["feed"]),
        ("Logs", lambda: show_frame(frames["logs"]), icons["logs"]),
        ("Config", lambda: show_frame(frames["config"]), icons["config"]),
        ("Hardware", lambda: show_frame(frames["hardware"]), icons["hardware"]),
        # ("Wi-Fi", lambda: show_frame(frames["wifi"]), icons["wifi"]),
        ("Admin", lambda: show_frame(frames["admin"]), icons["admin"]),
        ("Minimize", toggle_minimize_maximize, icons["minimize"]),
    ]

    for i, (label, cmd, icon) in enumerate(home_buttons):
        cell = tk.Frame(icon_frame, bg=theme["bg"])
        cell.grid(row=i // 3, column=i % 3, padx=40, pady=20)
        if label == "Minimize":
            global minimize_btn
            minimize_btn = make_label_button(cell, label, cmd, image=icon)
        else:
            make_label_button(cell, label, cmd, image=icon)

    # Access Panel
    access = frames["feed"]
    tk.Label(access, text="Live Feed", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=20)
    tk.Label(access, text="Camera Feed Here", bg="black", fg="white", width=120, height=22).pack(pady=10)

    back_btn = make_label_button(access, "", lambda: show_frame(home), image=icons["back"])
    back_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    # Logs Viewer
    logs = frames["logs"]
    tk.Label(logs, text="Access Logs", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=10)
    log_list = tk.Text(logs, wrap=tk.NONE, bg=theme["bg"], fg=theme["fg"], width=100, height=20)
    log_list.pack(pady=5)

    def refresh_logs():
        log_list.delete('1.0', tk.END)
        for entry in load_logs():
            log_list.insert(tk.END, f"{entry['timestamp']} | {entry['uid']} | {entry['name']} | {entry['status']}\n")

    footer = tk.Frame(logs, bg=theme["bg"])
    footer.pack(pady=10)
    make_label_button(footer, "Refresh", refresh_logs, icons["refresh"])
    make_label_button(footer, "Export", export_logs_to_csv, icons["export"])
    back_btn = make_label_button(logs, "", lambda: show_frame(home), image=icons["back"])
    back_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    # Config Screen
    config_tab = frames["config"]

    config_tab.place(relx=0.5, rely=0.5, anchor="center")
    tk.Label(config_tab, text="Config Editor", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=20)

    tk.Label(config_tab, text="Admin PIN:", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack()
    admin_pin_entry = tk.Entry(config_tab, show="*", font=("Helvetica", 24), bg=theme["accent"], fg=theme["fg"])
    admin_pin_entry.insert(0, config.get("admin_pin", ""))
    admin_pin_entry.pack()

    def on_theme_change():
        config["theme_mode"] = theme_var.get()
        save_config(config)
        reload_theme(root, frames, config)

    theme_var = tk.StringVar(value=config.get("theme_mode", "system"))

    theme_frame = tk.Frame(config_tab, bg=theme["bg"])
    theme_frame.pack(pady=10)

    tk.Label(theme_frame, text="Theme Mode:", font=("Helvetica", 18), bg=theme["bg"], fg=theme["fg"]).pack(side="left",
                                                                                                           padx=10)

    for label, value in [("Day", "day"), ("Night", "night"), ("System", "system")]:
        rb = tk.Radiobutton(
            theme_frame, text=label, variable=theme_var, value=value,
            font=("Helvetica", 16), bg=theme["bg"], fg=theme["fg"],
            selectcolor=theme["accent"], command=on_theme_change
        )
        rb.pack(side="left", padx=5)

    def save_cfg():
        config["admin_pin"] = admin_pin_entry.get()
        config["theme_mode"] = theme_var.get()
        save_config(config)
        reload_theme(root, frames, config)
        messagebox.showinfo("Saved", "Configuration saved and theme applied.")

    footer = tk.Frame(config_tab, bg=theme["bg"])
    footer.pack(pady=20)
    make_label_button(footer, "", save_cfg, image=icons["save"])
    back_btn = make_label_button(config_tab, "", lambda: show_frame(home), image=icons["back"])
    back_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    # Wi-Fi Screen
    # wifi = frames["wifi"]
    # wifi.place(relx=0.5, rely=0.5, anchor="center")
    # wifi_config = load_wifi_config()
    # tk.Label(wifi, text="Wi-Fi Settings", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=20)
    #
    # wifi_content = tk.Frame(wifi, bg=theme["bg"])
    # wifi_content.place(relx=0.5, rely=0.5, anchor="center")
    #
    # tk.Label(wifi, text="Current SSID:", font=("Helvetica", 20), bg=theme["bg"], fg=theme["fg"]).pack()
    # current_ssid_label = tk.Label(wifi, text=wifi_config.get("ssid", ""), font=("Helvetica", 20), bg=theme["bg"],
    #                               fg=theme["fg"])
    # current_ssid_label.pack()
    #
    # tk.Label(wifi, text="SSID:", font=("Helvetica", 20), bg=theme["bg"], fg=theme["fg"]).pack()
    # ssid_entry = tk.Entry(wifi, font=("Helvetica", 20), bg=theme["accent"], fg=theme["fg"])
    # ssid_entry.insert(0, wifi_config.get("ssid", ""))
    # ssid_entry.pack()
    #
    # tk.Label(wifi, text="Password:", font=("Helvetica", 20), bg=theme["bg"], fg=theme["fg"]).pack()
    # password_entry = tk.Entry(wifi, font=("Helvetica", 20), bg=theme["accent"], fg=theme["fg"])
    # password_entry.insert(0, wifi_config.get("password", ""))
    # password_entry.pack()
    #
    # keyboard_label = tk.Label(wifi, text="🧠 Keyboard", font=("Arial", 12, "bold"),
    #                           bg=theme["bg"], fg=theme["fg"], cursor="hand2")
    # keyboard_label.pack(pady=5)
    # keyboard_label.bind("<Button-1>", lambda e: launch_keyboard(wifi))
    #
    # def update_wifi():
    #     ssid = ssid_entry.get().strip()
    #     password = password_entry.get().strip()
    #     save_wifi_config(ssid, password)
    #     if write_to_wpa_supplicant(ssid, password):
    #         restart_wifi()
    #         current_ssid_label.config(text=ssid)
    #         messagebox.showinfo("Wi-Fi", "Wi-Fi settings applied.")
    #     else:
    #         messagebox.showerror("Error", "Permission denied. Try running with sudo.")
    #
    # footer = tk.Frame(wifi, bg=theme["bg"])
    # footer.pack(pady=20)
    # make_label_button(footer, "", update_wifi, image=icons["save"])
    # back_btn = make_label_button(wifi, "", lambda: show_frame(home), image=icons["back"])
    # back_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    # Hardware Test Tab
    hardware_tab = frames["hardware"]
    hardware_tab.place(relx=0.5, rely=0.5, anchor="center", relwidth=1, relheight=1)
    tk.Label(hardware_tab, text="Hardware Test Panel", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(
        pady=20)

    hardware_buttons = tk.Frame(hardware_tab, bg=theme["bg"])
    hardware_buttons.pack(pady=20)  # Ensure the frame is packed

    # Status Area
    status_var = tk.StringVar(value="Status: Awaiting test")
    status_label = tk.Label(hardware_tab, textvariable=status_var, font=("Arial", 14), bg=theme["bg"],
                            fg=theme["fg"])
    status_label.pack(pady=10)

    status_list = tk.Text(hardware_tab, wrap=tk.NONE, bg=theme["bg"], fg=theme["fg"], width=50, height=10)
    status_list.pack(side="left", fill="both", expand=True, pady=5)

    v_scroll = tk.Scrollbar(status_list, orient="vertical", command=status_list.yview)
    v_scroll.pack(side="right", fill="y")
    status_list.config(yscrollcommand=v_scroll.set)
    h_scroll = tk.Scrollbar(status_list, orient="horizontal", command=status_list.xview)
    h_scroll.pack(side="bottom", fill="x")
    status_list.config(xscrollcommand=h_scroll.set)

    def update_status(message):
        status_var.set(f"Status: {message}")
        status_list.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} | {message}\n")

    def test_rfid_scan():
        try:
            reader = SimpleMFRC522()
            update_status("Place card near reader...")
            root.update_idletasks()
            uid, text = reader.read()
            status_msg = f"RFID UID: {uid}"
            update_status(status_msg)
            last_uid.set(str(uid))  # Update the UID label in Card Manager
            messagebox.showinfo("RFID Scan", status_msg)
        except Exception as e:
            update_status(f"RFID Error: {e}")
            messagebox.showerror("RFID Error", str(e))
        finally:
            GPIO.cleanup()

    def test_keypad():
        messagebox.showinfo("Keypad", "Simulated PIN entered: 4321")
        update_status("Simulated keypad input: 4321")

    def test_relay():
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(26, GPIO.OUT)
            GPIO.output(26, GPIO.HIGH)
            root.after(1000, lambda: GPIO.output(26, GPIO.LOW))
            update_status("Relay triggered on GPIO 26")
        except Exception as e:
            update_status(f"Relay Error: {e}")
            messagebox.showerror("Relay Error", str(e))

    def test_led():
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(26, GPIO.OUT)  # <--- changed to match your wiring
            for _ in range(3):
                GPIO.output(26, GPIO.HIGH)
                root.update()
                root.after(200)
                GPIO.output(26, GPIO.LOW)
                root.after(200)
            update_status("LED blinked on GPIO 26")
        except Exception as e:
            update_status(f"LED Error: {e}")
            messagebox.showerror("LED Error", str(e))

    def test_camera():
        try:
            frame_img = get_mock_frame()
            path = take_snapshot("test")
            update_status(f"Camera snapshot saved to {path}")
            messagebox.showinfo("Camera", f"Snapshot saved to {path}")
        except Exception as e:
            update_status(f"Camera Error: {e}")
            messagebox.showerror("Camera Error", str(e))

    make_label_button(hardware_buttons, "RFID", test_rfid_scan, icons["rfid"])
    make_label_button(hardware_buttons, "Keypad", test_keypad, icons["keypad"])
    make_label_button(hardware_buttons, "Relay", test_relay, icons["relay"])
    make_label_button(hardware_buttons, "LED", test_led, icons["led"])
    make_label_button(hardware_buttons, "Camera", test_camera, icons["camera"])

    # GPIO Pin Reference
    # pin_frame = tk.Frame(frames["hardware"], bg=theme["bg"])
    # pin_frame.pack(pady=10)
    #
    # pin_label = tk.Label(pin_frame, text="""GPIO Pin Reference:
    # RFID-RC522:
    #   SDA  → GPIO 8
    #   SCK  → GPIO 11
    #   MOSI → GPIO 10
    #   MISO → GPIO 9
    #   RST  → GPIO 25
    #
    # Keypad:
    #   Rows/Cols → GPIO 2–9
    #
    # Relay:
    #   IN1 → GPIO 26
    #
    # Test LED:
    #   Anode → GPIO 17 (220Ω resistor)
    #   Cathode → GND
    # """, font=("Courier", 10), justify="left", bg=theme["bg"], fg=theme["fg"])
    # pin_label.pack()

    footer = tk.Frame(hardware_tab, bg=theme["bg"])
    footer.pack(pady=20)
    back_btn = make_label_button(hardware_tab, "", lambda: show_frame(home), image=icons["back"])
    back_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    # Admin Panel
    admin_tab = frames["admin"]
    tk.Label(admin_tab, text="Admin Panel", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=20)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours = [f"{h:02d}:00" for h in range(24)]
    blackout_settings = config.get("blackout", {})

    admin_tabs = ttk.Notebook(admin_tab)
    admin_tabs.pack(expand=True, fill="both")

    # Create a ttk.Style object
    style = ttk.Style()

    # Configure the TNotebook.Tab style
    style.configure("TNotebook.Tab", font=("Helvetica", 16))  # Change font to Helvetica, size 16

    # --- Blackout Tab ---
    blackout_tab = tk.Frame(admin_tabs, bg=theme["bg"])
    admin_tabs.add(blackout_tab, text="Blackout Schedule")

    tk.Label(blackout_tab, text="Blackout Schedule", font=("Helvetica", 20),
             bg=theme["bg"], fg=theme["fg"]).pack(pady=(10, 20))

    blackout_settings = config.get("blackout", {})
    day_widgets = {}

    for day in days:
        row = tk.Frame(blackout_tab, bg=theme["bg"])
        row.pack(pady=5)

        tk.Label(row, text=day, font=("Arial", 16, "bold"), width=5,
                 bg=theme["bg"], fg=theme["fg"]).pack(side="left", padx=(0, 10))

        start_var = tk.StringVar()
        end_var = tk.StringVar()
        all_day_var = tk.BooleanVar()

        start_dropdown = ttk.Combobox(row, textvariable=start_var, font=("Arial", 16), values=hours, width=6,
                                      state="readonly")
        end_dropdown = ttk.Combobox(row, textvariable=end_var, font=("Arial", 16), values=hours, width=6,
                                    state="readonly")
        start_dropdown.pack(side="left", padx=5)
        tk.Label(row, text="→", font=("Arial", 16), bg=theme["bg"], fg=theme["fg"]).pack(side="left")
        end_dropdown.pack(side="left", padx=5)

        def toggle_disable(s=start_dropdown, e=end_dropdown, v=all_day_var):
            state = "disabled" if v.get() else "readonly"
            s.configure(state=state)
            e.configure(state=state)

        all_day_chk = tk.Checkbutton(row, text="All Day", font=("Arial", 16), variable=all_day_var,
                                     command=lambda s=start_dropdown, e=end_dropdown, v=all_day_var: toggle_disable(s,
                                                                                                                    e,
                                                                                                                    v),
                                     bg=theme["bg"], fg=theme["fg"], selectcolor=theme["accent"])
        all_day_chk.pack(side="left", padx=10)

        saved = blackout_settings.get(day, {})
        start_var.set(f"{saved.get('start', 0):02d}:00")
        end_var.set(f"{saved.get('end', 0):02d}:00")
        all_day_var.set(saved.get("all_day", False))
        toggle_disable(start_dropdown, end_dropdown, all_day_var)

        day_widgets[day] = {
            "start": start_var,
            "end": end_var,
            "all_day": all_day_var
        }

    def save_blackout():
        blackout_config = {}
        for day in days:
            start = int(day_widgets[day]["start"].get().split(":")[0])
            end = int(day_widgets[day]["end"].get().split(":")[0])
            all_day = day_widgets[day]["all_day"].get()
            blackout_config[day] = {"start": start, "end": end, "all_day": all_day}
        config["blackout"] = blackout_config
        save_config(config)
        messagebox.showinfo("Saved", "Blackout schedule saved.")

    tk.Button(blackout_tab, text="Save Blackout", command=save_blackout,
              font=("Arial", 14), bg=theme["accent"], fg=theme["fg"]).pack(pady=10)
    # Save and Back controls
    footer = tk.Frame(blackout_tab, bg=theme["bg"])
    footer.pack(pady=20)
    back_btn = make_label_button(blackout_tab, "", lambda: show_frame(home), image=icons["back"])
    back_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)


    # --- Card Manager Tab ---
    from storage import load_users, save_config

    card_tab = tk.Frame(admin_tabs, bg=theme["bg"])
    admin_tabs.add(card_tab, text="Card Manager")

    tk.Label(card_tab, text="Assign Card to User", font=("Helvetica", 20), bg=theme["bg"], fg=theme["fg"]).pack(
        pady=10)

    last_uid = tk.StringVar(value="12345678")
    tk.Label(card_tab, text="Last Scanned UID:", font=("Arial", 16), bg=theme["bg"], fg=theme["fg"]).pack()
    tk.Label(card_tab, textvariable=last_uid, font=("Arial", 16), bg=theme["bg"], fg=theme["fg"]).pack()

    name_entry = tk.Entry(card_tab, font=("Arial", 16), bg=theme["accent"], fg=theme["fg"])
    name_entry.pack(pady=10)
    name_entry.insert(0, "User Name")

    is_admin_var = tk.BooleanVar()
    tk.Checkbutton(card_tab, text="Grant Admin Access", variable=is_admin_var,
                   bg=theme["bg"], fg=theme["fg"], selectcolor=theme["accent"], font=("Arial", 14)).pack(pady=5)

    def save_user():
        uid = last_uid.get()
        name = name_entry.get().strip()
        is_admin = is_admin_var.get()
        if not name:
            messagebox.showerror("Error", "Please enter a name.")
            return
        users = load_users()
        users[uid] = {"name": name, "admin": is_admin}
        config["users"] = users
        save_config(config)
        messagebox.showinfo("Saved", f"Assigned {name} to UID {uid}.")

    tk.Button(card_tab, text="Save Assignment", command=save_user,
              font=("Arial", 14), bg=theme["accent"], fg=theme["fg"]).pack(pady=10)

    # Save and Back controls
    footer = tk.Frame(card_tab, bg=theme["bg"])
    footer.pack(pady=20)
    back_btn = make_label_button(card_tab, "", lambda: show_frame(home), image=icons["back"])
    back_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    show_frame(home)
    print("[INFO] Starting GateWise UI")
    start_live_detection()
    print("[INFO] RFID reader thread running")

    update_frame()
    print("[INFO] Frame updated")  # You can throttle this for performance later
    root.mainloop()

