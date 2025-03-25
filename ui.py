# ui.py (final GateWise version)
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from PIL import Image, ImageTk
import subprocess

from camera import get_mock_frame, take_mock_snapshot
from storage import (
    log_access, load_users, load_config,
    save_config, load_logs, export_logs_to_csv,
    is_blackout
)
from wifi import load_wifi_config, save_wifi_config, write_to_wpa_supplicant, restart_wifi

# Theme Definitions
DAY_THEME = {"bg": "#ffffff", "fg": "#000000", "accent": "#dddddd", "button": "#f0f0f0"}
NIGHT_THEME = {"bg": "#294856", "fg": "#000000", "accent": "#3a3a3a", "button": "#2d2d2d"}

theme_mode = None
theme = {}

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

def load_and_resize_image(path, size):
    img = Image.open(path)
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)

def launch_keyboard(widget=None):
    subprocess.Popen(["matchbox-keyboard"])

def make_label_button(parent, text, command, image=None):
    lbl = tk.Label(parent, text=text, image=image, font=("Arial", 12),
                   fg=theme["fg"], bg=theme["bg"], cursor="hand2", compound="top", width=80)
    lbl.bind("<Button-1>", lambda e: command())
    lbl.bind("<Enter>", lambda e: lbl.config(bg=theme["accent"]))
    lbl.bind("<Leave>", lambda e: lbl.config(bg=theme["bg"]))
    lbl.pack(side="left", padx=10, pady=10)
    return lbl

def run_ui():
    global theme, theme_mode
    users = load_users()
    config = load_config()
    theme_mode = config.get("theme_mode", "system")
    theme = determine_theme(theme_mode)

    root = tk.Tk()
    root.title("GateWise Access Control")
    root.geometry("1024x600")
    root.attributes("-fullscreen", True)
    root.configure(bg=theme["bg"])

    # Load Icons
    icons = {
        "access": load_and_resize_image("assets/icons/access-control-dark.png", (100, 100)),
        "logs": load_and_resize_image("assets/icons/logs-dark.png", (100, 100)),
        "config": load_and_resize_image("assets/icons/settings-dark.png", (100, 100)),
        "wifi": load_and_resize_image("assets/icons/wifi-dark.png", (100, 100)),
        "admin": load_and_resize_image("assets/icons/admin-dark.png", (100, 100)),
        "minimize": load_and_resize_image("assets/icons/minimize-dark.png", (50, 50)),
        "refresh": load_and_resize_image("assets/icons/refresh-light.png", (50, 50)),
        "export": load_and_resize_image("assets/icons/export-dark.png", (50, 50)),
        "save": load_and_resize_image("assets/icons/save-dark.png", (50, 50)),
        "back": load_and_resize_image("assets/icons/back-dark.png", (50, 50)),
        "scan": load_and_resize_image("assets/icons/scan-dark.png", (70, 70)),
        "logo": load_and_resize_image("assets/icons/Gatewise-thumbnail.PNG", (50, 50)),
    }

    # Page container
    frames = {}
    for name in ["home", "access", "logs", "config", "wifi", "admin"]:
        frame = tk.Frame(root, bg=theme["bg"])
        frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=1, relheight=1)
        frames[name] = frame

        # Clock
        clock_label = tk.Label(frame, font=("Arial", 14), fg=theme["fg"], bg=theme["bg"])
        clock_label.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
        def update_clock(lbl=clock_label):
            lbl.config(text=datetime.now().strftime("%m-%d-%Y %H:%M"))
            lbl.after(1000, update_clock)
        update_clock()

    def show_frame(f):
        f.tkraise()

    def minimize_app():
        root.attributes("-fullscreen", False)
        root.iconify()

    def simulate_scan(uid="12345678"):
        frame_img = get_mock_frame()
        snapshot_path = take_mock_snapshot(uid, frame_img)
        status = "granted" if uid in users else "denied"
        name = users.get(uid, {}).get("name", "Unknown")
        if is_blackout(config) and not users.get(uid, {}).get("admin", False):
            status = "denied (blackout)"
        log_access(uid, name, status, snapshot_path)
        messagebox.showinfo("Scan Result", f"UID: {uid}\nName: {name}\nAccess: {status}")

    # Home screen
    home = frames["home"]
    tk.Label(home, text="GateWise", font=("Helvetica", 28, "bold"), bg=theme["bg"], fg=theme["fg"]).pack(pady=(20, 10))
    tk.Label(home, image=icons["logo"], bg=theme["bg"]).pack()

    icon_frame = tk.Frame(home, bg=theme["bg"])
    icon_frame.pack(pady=30)

    home_buttons = [
        ("Access", lambda: show_frame(frames["access"]), icons["access"]),
        ("Logs", lambda: show_frame(frames["logs"]), icons["logs"]),
        ("Config", lambda: show_frame(frames["config"]), icons["config"]),
        ("Wi-Fi", lambda: show_frame(frames["wifi"]), icons["wifi"]),
        ("Admin", lambda: show_frame(frames["admin"]), icons["admin"]),
        ("Minimize", minimize_app, icons["minimize"]),
    ]

    for i, (label, cmd, icon) in enumerate(home_buttons):
        cell = tk.Frame(icon_frame, bg=theme["bg"])
        cell.grid(row=i//3, column=i%3, padx=40, pady=20)
        make_label_button(cell, label, cmd, image=icon)

    # Access Panel
    access = frames["access"]
    tk.Label(access, text="Access Panel", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=20)
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
    wifi = frames["wifi"]
    wifi.place(relx=0.5, rely=0.5, anchor="center")
    wifi_config = load_wifi_config()
    tk.Label(wifi, text="Wi-Fi Settings", font=("Helvetica", 24), bg=theme["bg"], fg=theme["fg"]).pack(pady=20)

    wifi_content = tk.Frame(wifi, bg=theme["bg"])
    wifi_content.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(wifi, text="Current SSID:", font=("Helvetica", 20), bg=theme["bg"], fg=theme["fg"]).pack()
    current_ssid_label = tk.Label(wifi, text=wifi_config.get("ssid", ""), font=("Helvetica", 20), bg=theme["bg"],
                                  fg=theme["fg"])
    current_ssid_label.pack()

    tk.Label(wifi, text="SSID:", font=("Helvetica", 20), bg=theme["bg"], fg=theme["fg"]).pack()
    ssid_entry = tk.Entry(wifi, font=("Helvetica", 20), bg=theme["accent"], fg=theme["fg"])
    ssid_entry.insert(0, wifi_config.get("ssid", ""))
    ssid_entry.pack()

    tk.Label(wifi, text="Password:", font=("Helvetica", 20), bg=theme["bg"], fg=theme["fg"]).pack()
    password_entry = tk.Entry(wifi, font=("Helvetica", 20), bg=theme["accent"], fg=theme["fg"])
    password_entry.insert(0, wifi_config.get("password", ""))
    password_entry.pack()

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
    make_label_button(footer, "", update_wifi, image=icons["save"])
    back_btn = make_label_button(wifi, "", lambda: show_frame(home), image=icons["back"])
    back_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

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
    make_label_button(footer, "", save_blackout, image=icons["save"])
    back_btn = make_label_button(admin_tab, "", lambda: show_frame(home), image=icons["back"])
    back_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

    keyboard_label = tk.Label(admin_content, text="🧠 Keyboard", font=("Arial", 12, "bold"),
                              bg=theme["bg"], fg=theme["fg"], cursor="hand2")
    keyboard_label.pack(pady=5)
    keyboard_label.bind("<Button-1>", lambda e: launch_keyboard())

    show_frame(home)
    root.mainloop()
