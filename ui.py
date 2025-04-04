import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import socket
import json
import threading
from PIL import Image, ImageTk
import subprocess
from storage import (
    load_config, save_config, load_logs, export_logs_to_csv
)

# Themes
DAY_THEME = {"bg": "#ffffff", "fg": "#000000", "accent": "#dddddd"}
NIGHT_THEME = {"bg": "#294856", "fg": "#ffffff", "accent": "#3a3a3a"}

theme = {}
theme_mode = None
is_minimized = False

monitor_events = []
monitor_filters = {"status": "All", "door": "All"}
TCP_PORT = 5005

def determine_theme(mode):
    hour = datetime.now().hour
    if mode == "day":
        return DAY_THEME
    elif mode == "night":
        return NIGHT_THEME
    elif mode == "system":
        return DAY_THEME if 7 <= hour < 19 else NIGHT_THEME
    return DAY_THEME


def reload_theme(root, frames, config):
    global theme, theme_mode
    theme_mode = config.get("theme_mode", "system")
    theme = determine_theme(theme_mode)
    root.configure(bg=theme["bg"])

    for frame in frames.values():
        frame.configure(bg=theme["bg"])
        for widget in frame.winfo_children():
            try:
                widget.configure(bg=theme["bg"], fg=theme["fg"])
            except:
                pass


def load_and_resize_image(path, size):
    img = Image.open(path)
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def make_label_button(parent, text, command, image=None):
    lbl = tk.Label(parent, text=text, image=image, font=("Arial", 16),
                   fg=theme["fg"], bg=theme["bg"], cursor="hand2",
                   padx=10, pady=10, compound="top", width=90)
    lbl.bind("<Button-1>", lambda e: command())
    lbl.bind("<Enter>", lambda e: lbl.config(bg=theme["accent"]))
    lbl.bind("<Leave>", lambda e: lbl.config(bg=theme["bg"]))
    lbl.pack(side="left", padx=10, pady=10)
    return lbl

def start_tcp_listener(update_monitor_callback):
    def listen():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", TCP_PORT))
        s.listen()

        print(f"[TCP] Listening on port {TCP_PORT}...")

        while True:
            conn, addr = s.accept()
            with conn:
                try:
                    data = conn.recv(1024).decode("utf-8")
                    if data:
                        print("[TCP] Received:", data)
                        event = json.loads(data)
                        event["timestamp"] = datetime.now().strftime("%H:%M:%S")
                        monitor_events.append(event)
                        update_monitor_callback()
                except Exception as e:
                    print("[TCP] Error:", e)

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()

def send_unlock_command(ip, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(b"UNLOCK")
        messagebox.showinfo("Sent", f"Unlock command sent to {ip}:{port}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to send unlock: {e}")

def send_command_to_door(ip, command):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, 5050))
            s.sendall(command.encode())
            print(f"[CMD] Sent '{command}' to {ip}")
    except Exception as e:
        print(f"[CMD] Error sending to {ip}:", e)


def run_ui():
    global theme, theme_mode

    config = load_config()
    theme_mode = config.get("theme_mode", "system")
    theme = determine_theme(theme_mode)

    root = tk.Tk()
    root.title("GateWise Main Station")
    root.geometry("1024x600")
    root.attributes("-fullscreen", True)
    root.configure(bg=theme["bg"])

    icons = {
        "logo": load_and_resize_image("assets/icons/Gatewise.PNG", (100, 100)),
        "logs": load_and_resize_image("assets/icons/logs-white.png", (80, 80)),
        "config": load_and_resize_image("assets/icons/config_white.png", (80, 80)),
        "admin": load_and_resize_image("assets/icons/admin_white.png", (80, 80)),
        "minimize": load_and_resize_image("assets/icons/minimize_white.png", (80, 80)),
        "maximize": load_and_resize_image("assets/icons/maximize_white.png", (80, 80)),
        "refresh": load_and_resize_image("assets/icons/refresh_white.png", (50, 50)),
        "export": load_and_resize_image("assets/icons/export_white.png", (50, 50)),
        "save": load_and_resize_image("assets/icons/save_white.png", (50, 50)),
        "back": load_and_resize_image("assets/icons/back_white.png", (50, 50)),
        "camera": load_and_resize_image("assets/icons/camera_white.png", (50, 50)),
        "relay": load_and_resize_image("assets/icons/relay_white.png", (50, 50)),
    }

    # Frame container
    frames = {}
    for name in ["home", "logs", "config", "admin", "monitor"]:
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

    def maximize_app():
        global is_minimized
        root.deiconify()
        root.attributes("-fullscreen", True)
        is_minimized = False

    def toggle_minimize_maximize():
        if is_minimized:
            maximize_app()
        else:
            minimize_app()

    # Home screen
    home = frames["home"]
    tk.Label(home, image=icons["logo"], bg=theme["bg"]).pack(pady=20)

    icon_frame = tk.Frame(home, bg=theme["bg"])
    icon_frame.pack(pady=30)

    home_buttons = [
        ("Monitor", lambda: show_frame(frames["monitor"]), icons["camera"]),
        ("Logs", lambda: show_frame(frames["logs"]), icons["logs"]),
        ("Config", lambda: show_frame(frames["config"]), icons["config"]),
        ("Admin", lambda: show_frame(frames["admin"]), icons["admin"]),
        ("Minimize", toggle_minimize_maximize, icons["minimize"]),
        ("Unlock Main", lambda: send_unlock_command("192.168.0.101", 5051), icons["relay"]) # update IP
    ]

    for i, (label, cmd, icon) in enumerate(home_buttons):
        cell = tk.Frame(icon_frame, bg=theme["bg"])
        cell.grid(row=i // 3, column=i % 3, padx=40, pady=20)
        make_label_button(cell, label, cmd, image=icon)

    # Logs Viewer
    logs = frames["logs"]
    tk.Label(logs, text="Access Logs", font=("Helvetica", 24),
             bg=theme["bg"], fg=theme["fg"]).pack(pady=10)

    log_list = tk.Text(logs, wrap=tk.NONE, bg=theme["bg"], fg=theme["fg"],
                       width=100, height=20)
    log_list.pack(pady=5)

    def refresh_logs():
        log_list.delete('1.0', tk.END)
        for entry in load_logs():
            log_list.insert(tk.END, f"{entry['timestamp']} | {entry['uid']} | {entry['name']} | {entry['status']}\n")

    footer = tk.Frame(logs, bg=theme["bg"])
    footer.pack(pady=10)
    make_label_button(footer, "Refresh", refresh_logs, icons["refresh"])
    make_label_button(footer, "Export", export_logs_to_csv, icons["export"])
    make_label_button(logs, "", lambda: show_frame(home), image=icons["back"]).place(
        relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    # Config screen
    config_tab = frames["config"]
    tk.Label(config_tab, text="Config Editor", font=("Helvetica", 24),
             bg=theme["bg"], fg=theme["fg"]).pack(pady=20)

    tk.Label(config_tab, text="Admin PIN:", font=("Helvetica", 18),
             bg=theme["bg"], fg=theme["fg"]).pack()
    admin_pin_entry = tk.Entry(config_tab, show="*", font=("Helvetica", 18),
                               bg=theme["accent"], fg=theme["fg"])
    admin_pin_entry.insert(0, config.get("admin_pin", ""))
    admin_pin_entry.pack()

    theme_var = tk.StringVar(value=config.get("theme_mode", "system"))

    theme_frame = tk.Frame(config_tab, bg=theme["bg"])
    theme_frame.pack(pady=10)
    tk.Label(theme_frame, text="Theme Mode:", font=("Helvetica", 16),
             bg=theme["bg"], fg=theme["fg"]).pack(side="left", padx=10)

    def on_theme_change():
        config["theme_mode"] = theme_var.get()
        save_config(config)
        reload_theme(root, frames, config)

    for label, value in [("Day", "day"), ("Night", "night"), ("System", "system")]:
        rb = tk.Radiobutton(theme_frame, text=label, variable=theme_var, value=value,
                            font=("Helvetica", 14), bg=theme["bg"], fg=theme["fg"],
                            selectcolor=theme["accent"], command=on_theme_change)
        rb.pack(side="left", padx=5)

    def save_cfg():
        config["admin_pin"] = admin_pin_entry.get()
        config["theme_mode"] = theme_var.get()
        save_config(config)
        reload_theme(root, frames, config)
        messagebox.showinfo("Saved", "Configuration saved and theme applied.")

    make_label_button(config_tab, "", save_cfg, image=icons["save"]).pack(pady=10)
    make_label_button(config_tab, "", lambda: show_frame(home), image=icons["back"]).place(
        relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    # --- Admin Panel ---
    admin_tab = frames["admin"]
    tk.Label(admin_tab, text="Admin Panel", font=("Helvetica", 24),
             bg=theme["bg"], fg=theme["fg"]).pack(pady=10)

    admin_tabs = ttk.Notebook(admin_tab)
    admin_tabs.pack(expand=True, fill="both")

    style = ttk.Style()
    style.configure("TNotebook.Tab", font=("Helvetica", 16))

    # === BLACKOUT TAB ===
    blackout_tab = tk.Frame(admin_tabs, bg=theme["bg"])
    admin_tabs.add(blackout_tab, text="Blackout Schedule")

    # Split into scrollable top + fixed bottom
    blackout_top = tk.Frame(blackout_tab, bg=theme["bg"])
    blackout_top.pack(side="top", fill="both", expand=True)

    blackout_bottom = tk.Frame(blackout_tab, bg=theme["bg"])
    blackout_bottom.pack(side="bottom", fill="x")

    tk.Label(blackout_top, text="Advanced Blackout Schedule", font=("Helvetica", 20, "bold"),
             bg=theme["bg"], fg=theme["fg"]).pack(pady=(10, 10))

    # Scrollable horizontal blackout layout
    scroll_canvas = tk.Canvas(blackout_top, bg=theme["bg"], highlightthickness=0)
    h_scroll = tk.Scrollbar(blackout_top, orient="horizontal", command=scroll_canvas.xview)
    scroll_canvas.configure(xscrollcommand=h_scroll.set)

    scroll_canvas.pack(side="top", fill="both", expand=True, padx=10)
    h_scroll.pack(side="bottom", fill="x")

    scroll_frame = tk.Frame(scroll_canvas, bg=theme["bg"])
    scroll_canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

    def on_configure(event):
        scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

    scroll_frame.bind("<Configure>", on_configure)

    blackout_settings = config.get("blackout", {})
    day_block_widgets = {}

    def add_block_ui(day_frame, day, block_data=None):
        block_row = tk.Frame(day_frame, bg=theme["bg"])
        block_row.pack(pady=4, padx=5, anchor="w")

        try:
            start_hour = block_data["start"] if isinstance(block_data, dict) else 0
            end_hour = block_data["end"] if isinstance(block_data, dict) else 1
        except:
            start_hour, end_hour = 0, 1

        start_var = tk.StringVar(value=f"{start_hour:02d}:00")
        end_var = tk.StringVar(value=f"{end_hour:02d}:00")

        combo_style = {"font": ("Arial", 11), "width": 6, "state": "readonly"}
        time_values = [f"{h:02d}:00" for h in range(24)]

        ttk.Combobox(block_row, textvariable=start_var, values=time_values, **combo_style).pack(side="left", padx=2)
        tk.Label(block_row, text="→", font=("Arial", 12), bg=theme["bg"], fg=theme["fg"]).pack(side="left")
        ttk.Combobox(block_row, textvariable=end_var, values=time_values, **combo_style).pack(side="left", padx=2)

        tk.Button(block_row, text="✕", command=lambda: block_row.destroy(),
                  font=("Arial", 10), bg="#c0392b", fg="white", width=3, relief="flat").pack(side="left", padx=6)

        day_block_widgets[day].append((start_var, end_var))

    def create_day_column(day):
        day_frame = tk.LabelFrame(scroll_frame, text=day, font=("Arial", 14, "bold"),
                                  bg=theme["bg"], fg=theme["fg"], padx=8, pady=5, width=150)
        day_frame.pack(side="left", fill="y", expand=False, padx=10, pady=10)

        day_block_widgets[day] = []

        for block in blackout_settings.get(day, []):
            add_block_ui(day_frame, day, block)

        tk.Button(day_frame, text="+ Add Block", command=lambda: add_block_ui(day_frame, day),
                  font=("Arial", 10), bg=theme["accent"], fg=theme["fg"], relief="groove").pack(anchor="w", pady=5)

    # 7 Day Columns
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        create_day_column(day)

    # --- SAVE BUTTON ---
    def save_blackout():
        updated = {}
        for day, blocks in day_block_widgets.items():
            updated[day] = []
            for start_var, end_var in blocks:
                try:
                    start_hour = int(start_var.get().split(":")[0])
                    end_hour = int(end_var.get().split(":")[0])
                    updated[day].append({"start": start_hour, "end": end_hour})
                except:
                    continue
        config["blackout"] = updated
        save_config(config)
        messagebox.showinfo("Saved", "Blackout schedule saved.")

    tk.Button(blackout_bottom, text="Save Blackout", command=save_blackout,
              font=("Arial", 12), bg=theme["accent"], fg=theme["fg"], relief="raised").pack(side="right", padx=10,
                                                                                            pady=5)

    # === BOTTOM OVERRIDE CONTROLS ===
    def admin_unlock_all():
        from tkinter import simpledialog
        entered_pin = simpledialog.askstring("PIN", "Enter Admin PIN:", show="*")
        if entered_pin == config.get("admin_pin"):
            send_command_to_door("192.168.0.42", "UNLOCK")
            messagebox.showinfo("Override", "All doors unlocked.")
        else:
            messagebox.showerror("Access Denied", "Incorrect PIN.")

    def admin_lock_all():
        from tkinter import simpledialog
        entered_pin = simpledialog.askstring("PIN", "Enter Admin PIN:", show="*")
        if entered_pin == config.get("admin_pin"):
            send_command_to_door("192.168.0.42","LOCK")
            messagebox.showinfo("Override", "All doors locked.")
        else:
            messagebox.showerror("Access Denied", "Incorrect PIN.")

    button_frame = tk.Frame(admin_tab, bg=theme["bg"])
    button_frame.pack(side="bottom", fill="x", pady=5)

    tk.Button(button_frame, text="🔓 Unlock All", command=admin_unlock_all,
              font=("Arial", 14), bg="#27ae60", fg="white", padx=20, pady=5).pack(side="left", padx=10)

    tk.Button(button_frame, text="🔒 Lock All", command=admin_lock_all,
              font=("Arial", 14), bg="#c0392b", fg="white", padx=20, pady=5).pack(side="left", padx=10)

    # Optional: Back button
    make_label_button(admin_tab, "", lambda: show_frame(frames["home"]), image=icons["back"]).place(
        relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    # Live Monitor Tab
    monitor_tab = tk.Frame(root, bg=theme["bg"])
    monitor_tab.place(relx=0.5, rely=0.5, anchor="center", relwidth=1, relheight=1)
    frames["monitor"] = monitor_tab

    tk.Label(monitor_tab, text="Live Monitor", font=("Helvetica", 24),
             bg=theme["bg"], fg=theme["fg"]).pack(pady=10)

    filter_frame = tk.Frame(monitor_tab, bg=theme["bg"])
    filter_frame.pack(pady=5)

    # Filter dropdowns
    door_var = tk.StringVar(value="All")
    status_var = tk.StringVar(value="All")
    doors = ["All", "door1", "door2", "door3"]
    statuses = ["All", "granted", "denied"]

    ttk.Label(filter_frame, text="Door:", background=theme["bg"], foreground=theme["fg"]).pack(side="left", padx=5)
    ttk.Combobox(filter_frame, textvariable=door_var, values=doors, state="readonly", width=10).pack(side="left", padx=5)
    ttk.Label(filter_frame, text="Status:", background=theme["bg"], foreground=theme["fg"]).pack(side="left", padx=5)
    ttk.Combobox(filter_frame, textvariable=status_var, values=statuses, state="readonly", width=10).pack(side="left", padx=5)

    monitor_list = tk.Text(monitor_tab, bg=theme["bg"], fg=theme["fg"], width=100, height=20)
    monitor_list.pack(pady=10)

    def update_monitor_display():
        monitor_list.delete(1.0, tk.END)
        for event in reversed(monitor_events[-100:]):
            if (door_var.get() != "All" and event.get("door") != door_var.get()):
                continue
            if (status_var.get() != "All" and event.get("status") != status_var.get()):
                continue
            line = f"{event['timestamp']} | Door: {event.get('door')} | UID: {event.get('uid')} | Name: {event.get('name')} | Status: {event.get('status')}\n"
            monitor_list.insert(tk.END, line)

    # Hook filters to update the display
    door_var.trace("w", lambda *args: update_monitor_display())
    status_var.trace("w", lambda *args: update_monitor_display())

    back_btn = make_label_button(monitor_tab, "", lambda: show_frame(frames["home"]), image=icons["back"])
    back_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    # Start the TCP listener
    start_tcp_listener(update_monitor_display)


    show_frame(home)
    root.mainloop()
