
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, PhotoImage
from datetime import datetime
from camera import get_mock_frame, take_mock_snapshot
from storage import (
    log_access, load_users, load_config,
    save_config, load_logs, export_logs_to_csv,
    is_blackout
)
from wifi import load_wifi_config, save_wifi_config, write_to_wpa_supplicant, restart_wifi
import subprocess
from PIL import Image, ImageTk

DAY_THEME = {
    "bg": "#ffffff",
    "fg": "#000000",
    "accent": "#dddddd",
    "button": "#f0f0f0"
}

NIGHT_THEME = {
    "bg": "#1e1e1e",
    "fg": "#ffffff",
    "accent": "#3a3a3a",
    "button": "#2d2d2d"
}

theme_mode = None
theme = {}

def simulate_scan(uid="12345678"):
    from camera import get_mock_frame, take_mock_snapshot
    from storage import load_users, log_access, is_blackout, load_config
    config = load_config()
    users = load_users()
    frame_img = get_mock_frame()
    snapshot_path = take_mock_snapshot(uid, frame_img)
    status = "granted" if uid in users else "denied"
    name = users.get(uid, {}).get("name", "Unknown")
    if is_blackout(config) and not users.get(uid, {}).get("admin", False):
        status = "denied (blackout)"
    log_access(uid, name, status, snapshot_path)
    print(f"[SIMULATED RFID] UID: {uid}, Name: {name}, Status: {status}")

def simulate_keypad(pin="1234"):
    from storage import load_config
    config = load_config()
    if pin == config.get("admin_pin"):
        print("[SIMULATED KEYPAD] Admin override successful.")
    else:
        print("[SIMULATED KEYPAD] Incorrect PIN entered.")

def launch_system_keyboard():
    subprocess.Popen(["matchbox-keyboard"])

def determine_theme(mode):
    hour = datetime.now().hour
    if mode == "day":
        return DAY_THEME
    elif mode == "night":
        return NIGHT_THEME
    elif mode == "system":
        return DAY_THEME if 7 <= hour < 19 else NIGHT_THEME
    return DAY_THEME

def run_ui():
    global theme, theme_mode
    users = load_users()
    config = load_config()
    theme_mode = config.get("theme_mode", "system")
    theme = determine_theme(theme_mode)

    root = tk.Tk()
    root.title("Gym Access Panel")
    root.geometry("1024x600")
    root.attributes("-fullscreen", True)
    root.configure(bg=theme["bg"])

    def show_frame(frame):
        frame.tkraise()

    def verify_admin_exit():
        pin = simpledialog.askstring("Admin Exit", "Enter Admin PIN:", show="*")
        if pin == config.get("admin_pin"):
            root.destroy()
        else:
            messagebox.showerror("Access Denied", "Invalid PIN.")

    def minimize_app():
        root.attributes("-fullscreen", False)
        root.iconify()

    # Frames
    frames = {}
    for name in ["home", "access", "logs", "config", "wifi", "admin"]:
        frame = tk.Frame(root, bg=theme["bg"])
        frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=1, relheight=1)
        frames[name] = frame
        clock_label = tk.Label(frame, font=("Arial", 14), fg=theme["fg"], bg=theme["bg"])
        clock_label.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

        def update_clock():
            now = datetime.now().strftime("%m-%d-%Y %H:%M")
            clock_label.config(text=now)
            clock_label.after(1000, update_clock)

        update_clock()

    # Home Icon Grid
    home = frames["home"]
    tk.Label(home, text="Gym Access Panel", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=10)

    icon_frame = tk.Frame(home, bg=theme["bg"])
    icon_frame.pack(expand=True)

    def load_and_resize_image(path, size):
        img = Image.open(path)
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    access_control_icon_dark = load_and_resize_image("assets/icons/access-control-dark.png", (50, 50))
    access_control_icon_light = load_and_resize_image("assets/icons/access-control-light.png", (50, 50))
    logs_icon_dark = load_and_resize_image("assets/icons/logs-dark.png", (50, 50))
    logs_icon_light = load_and_resize_image("assets/icons/logs-light.png", (50, 50))
    config_icon_dark = load_and_resize_image("assets/icons/settings-dark.png", (50, 50))
    config_icon_light = load_and_resize_image("assets/icons/settings-light.png", (50, 50))
    wifi_icon_dark = load_and_resize_image("assets/icons/wifi-dark.png", (50, 50))
    wifi_icon_light = load_and_resize_image("assets/icons/wifi-light.png", (50, 50))
    admin_icon_dark = load_and_resize_image("assets/icons/admin-dark.png", (50, 50))
    admin_icon_light = load_and_resize_image("assets/icons/admin-light.png", (50, 50))
    minimize_icon_dark = load_and_resize_image("assets/icons/minimize-dark.png", (50, 50))
    minimize_icon_light = load_and_resize_image("assets/icons/minimize-light.png", (50, 50))

    icons = [
        (access_control_icon_dark, "Access", lambda: show_frame(frames["access"])),
        (logs_icon_dark, "Logs", lambda: show_frame(frames["logs"])),
        (config_icon_dark, "Config", lambda: show_frame(frames["config"])),
        (wifi_icon_dark, "Wi-Fi", lambda: show_frame(frames["wifi"])),
        (admin_icon_dark, "Admin", lambda: show_frame(frames["admin"])),
        (minimize_icon_light, "Minimize", minimize_app)
    ]


    for i, (icon, label, cmd) in enumerate(icons):
        row = i // 3
        col = i % 3
        cell = tk.Frame(icon_frame, bg=theme["bg"])
        cell.grid(row=row, column=col, padx=40, pady=20)
        lbl = tk.Label(cell, text=label, image=icon, font=("Arial", 10), cursor="hand2", bg=theme["bg"], fg=theme["fg"])
        lbl.pack()
        lbl.bind("<Button-1>", lambda e, f=cmd: f())
        tk.Label(cell, text=label, font=("Arial", 14), bg=theme["bg"], fg=theme["fg"]).pack()


    # Access Panel
    access = frames["access"]
    tk.Label(access, text="Access Panel", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=20)

    # Camera feed (mock)

    # Camera feed (mock)
    frame = tk.Label(access, text="Camera Feed Here", bg="black", fg="white", width=60, height=15)
    frame.pack(pady=10)
    def make_label_button(parent, text, command):
        new_lbl = tk.Label(parent, text=text, font=("Arial", 20, "bold"),
                          fg=theme["fg"], bg=theme["bg"], cursor="hand2", width=12)
        new_lbl.bind("<Button-1>", lambda e: command())
        new_lbl.bind("<Enter>", lambda e: new_lbl.config(bg=theme["accent"]))
        new_lbl.bind("<Leave>", lambda e: new_lbl.config(bg=theme["bg"]))
        new_lbl.pack(padx=5, pady=5, side="left")
        return new_lbl

    def make_toggle_label(parent, text, label_var):
        def toggle():
            label_var.set(not label_var.get())
            label_var.config(bg=theme["accent"] if label_var.get() else theme["bg"])

        label_var = tk.Label(parent, text=text, font=("Arial", 16),
                       fg=theme["fg"], bg=theme["accent"] if label_var.get() else theme["bg"],
                       cursor="hand2", relief="groove", width=3)
        label_var.bind("<Button-1>", lambda e: toggle())
        label_var.pack(side="left", padx=2, pady=2)
        return lbl

    def simulate_scan(uid="12345678"):
        frame_img = get_mock_frame()
        snapshot_path = take_mock_snapshot(uid, frame_img)
        status = "granted" if uid in users else "denied"
        user_name = users.get(uid, {}).get("name", "Unknown")
        if is_blackout(config) and not users.get(uid, {}).get("admin", False):
            status = "denied (blackout)"
        log_access(uid, user_name, status, snapshot_path)
        messagebox.showinfo("Scan Result", f"UID: {uid}\nName: {user_name}\nAccess: {status}")

    footer = tk.Frame(access, bg=theme["bg"])
    footer.pack(pady=20)
    make_label_button(footer, "🎫 Scan", simulate_scan)
    make_label_button(footer, "⬅", lambda: show_frame(home))

    # Logs Viewer
    logs = frames["logs"]
    tk.Label(logs, text="Access Logs", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=10)
    logs.place(relx=0.5, rely=0.5, anchor="center")
    log_list = tk.Text(logs, wrap=tk.NONE, bg=theme["bg"], fg=theme["fg"], width=100, height=20)
    log_list.pack(pady=5)

    def refresh_logs():
        log_list.delete('1.0', tk.END)
        for entry in load_logs():
            log_list.insert(tk.END, f"{entry['timestamp']} | {entry['uid']} | {entry['name']} | {entry['status']}\n")

    footer = tk.Frame(logs, bg=theme["bg"])
    footer.pack(pady=20)
    make_label_button(footer, "🔁", refresh_logs)
    make_label_button(footer, "📄 Export", lambda: export_logs_to_csv())
    make_label_button(footer, "⬅", lambda: show_frame(home))

    # Config Screen
    config_tab = frames["config"]
    tk.Label(config_tab, text="Config Editor", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=20)

    tk.Label(config_tab, text="Admin PIN:", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack()
    admin_pin_entry = tk.Entry(config_tab, show="*", font=("Helvetica", 24), bg=theme["accent"], fg=theme["fg"])
    admin_pin_entry.insert(0, config.get("admin_pin", ""))
    admin_pin_entry.pack()

    # Add a label to launch keyboard next to it
    keyboard_label = tk.Label(config_tab, text="🧠 Keyboard", font=("Arial", 12, "bold"),
                              bg=theme["bg"], fg=theme["fg"], cursor="hand2")
    keyboard_label.pack(pady=5)
    keyboard_label.bind("<Button-1>", lambda e: launch_keyboard(admin_pin_entry))

    def save_cfg():
        config["admin_pin"] = admin_pin_entry.get()
        save_config(config)
        messagebox.showinfo("Saved", "Configuration saved.")

    footer = tk.Frame(config_tab, bg=theme["bg"])
    footer.pack(pady=20)
    make_label_button(footer, "💾", save_cfg)
    make_label_button(footer, "⬅", lambda: show_frame(home))

    # Wi-Fi Screen
    wifi = frames["wifi"]
    wifi.place(relx=0.5, rely=0.5, anchor="center")
    wifi_config = load_wifi_config()
    tk.Label(wifi, text="Wi-Fi Settings", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=20)

    wifi_content = tk.Frame(wifi, bg=theme["bg"])
    wifi_content.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(wifi, text="Current SSID:", font=("Helvetica", 20), bg=theme["bg"], fg=theme["fg"]).pack()
    current_ssid_label = tk.Label(wifi, text=wifi_config.get("ssid", ""), font=("Helvetica", 20), bg=theme["bg"], fg=theme["fg"])
    current_ssid_label.pack()

    tk.Label(wifi, text="SSID:", font=("Helvetica", 20), bg=theme["bg"], fg=theme["fg"]).pack()
    ssid_entry = tk.Entry(wifi, font=("Helvetica", 20), bg=theme["accent"], fg=theme["fg"])
    ssid_entry.insert(0, wifi_config.get("ssid", ""))
    ssid_entry.pack()

    tk.Label(wifi, text="Password:", font=("Helvetica", 20), bg=theme["bg"], fg=theme["fg"]).pack()
    password_entry = tk.Entry(wifi,  font=("Helvetica", 20), bg=theme["accent"], fg=theme["fg"])
    password_entry.insert(0, wifi_config.get("password", ""))
    password_entry.pack()

    # Add a label to launch keyboard next to it
    keyboard_label = tk.Label(wifi, text="🧠 Keyboard", font=("Arial", 12, "bold"),
                              bg=theme["bg"], fg=theme["fg"], cursor="hand2")
    keyboard_label.pack(pady=5)
    keyboard_label.bind("<Button-1>", lambda e: launch_keyboard(wifi))

    def update_wifi():
        ssid = ssid_entry.get().strip()
        password = password_entry.get().strip()
        save_wifi_config(ssid, password)
        if write_to_wpa_supplicant(ssid, password):
            restart_wifi()
            current_ssid_label.config(text=ssid)
            messagebox.showinfo("Wi-Fi", "Wi-Fi settings applied.")
        else:
            messagebox.showerror("Error", "Permission denied. Try running with sudo.")

    footer = tk.Frame(wifi, bg=theme["bg"])
    footer.pack(pady=20)
    make_label_button(footer, "💾", update_wifi)
    make_label_button(footer, "⬅", lambda: show_frame(home))

    # Admin Panel (placeholder for blackout/schedule)
    admin_tab = frames["admin"]
    tk.Label(admin_tab, text="Admin Panel", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=20)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours = [f"{h:02d}:00" for h in range(24)]
    blackout_settings = config.get("blackout", {})

    admin_content = tk.Frame(admin_tab, bg=theme["bg"])
    admin_content.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(admin_content, text="🕒 Blackout Schedule", font=("Helvetica", 20),
             bg=theme["bg"], fg=theme["fg"]).pack(pady=(10, 20))

    day_widgets = {}

    for day in days:
        row = tk.Frame(admin_content, bg=theme["bg"])
        row.pack(pady=5)

        tk.Label(row, text=day, font=("Arial", 16, "bold"), width=5,
                 bg=theme["bg"], fg=theme["fg"]).pack(side="left", padx=(0, 10))

        start_var = tk.StringVar()
        end_var = tk.StringVar()
        all_day_var = tk.BooleanVar()

        start_dropdown = ttk.Combobox(row, textvariable=start_var, font=("Arial", 16), values=hours, width=6, state="readonly")
        end_dropdown = ttk.Combobox(row, textvariable=end_var, font=("Arial", 16), values=hours, width=6, state="readonly")
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

        # Load saved values
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

    # Save function
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

    # Save and Back controls
    footer = tk.Frame(admin_content, bg=theme["bg"])
    footer.pack(pady=20)
    make_label_button(footer, "💾", save_blackout)
    make_label_button(footer, "⬅", lambda: show_frame(home))
    # Add a label to launch keyboard next to it
    keyboard_label = tk.Label(admin_content, text="🧠 Keyboard", font=("Arial", 12, "bold"),
                              bg=theme["bg"], fg=theme["fg"], cursor="hand2")
    keyboard_label.pack(pady=5)
    keyboard_label.bind("<Button-1>", lambda e: launch_keyboard(entry))

    show_frame(home)
    root.mainloop()
