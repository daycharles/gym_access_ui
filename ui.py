
# UI WITH WIFI SETTINGS TAB (UPDATED)
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from camera import get_mock_frame, take_mock_snapshot
from storage import (
    log_access, load_users, load_config,
    save_config, load_logs, export_logs_to_csv,
    is_blackout
)
from wifi import load_wifi_config, save_wifi_config, write_to_wpa_supplicant, restart_wifi
from datetime import datetime

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

def apply_theme_to_widget(widget, theme):
    try:
        widget.configure(bg=theme["bg"], fg=theme["fg"])
    except:
        pass
    for child in widget.winfo_children():
        apply_theme_to_widget(child, theme)

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

    window = tk.Tk()
    window.title("Gym Access Panel")
    window.geometry("1024x600")
    window.configure(bg=theme["bg"])

    def reload_theme():
        global theme, theme_mode
        config = load_config()
        theme_mode = theme_var.get()
        config["theme_mode"] = theme_mode
        save_config(config)
        theme = determine_theme(theme_mode)
        window.configure(bg=theme["bg"])
        clock_label.configure(bg=theme["bg"], fg=theme["fg"])
        style.configure('TNotebook', background=theme["bg"])
        style.configure('TNotebook.Tab', background=theme["accent"], foreground=theme["fg"])
        style.configure('TFrame', background=theme["bg"])
        for tab in [access_tab, logs_tab, config_tab, wifi_tab]:
            tab.configure(bg=theme["bg"])
        for frame in [access_frame, logs_frame, config_frame, wifi_frame]:
            frame.configure(bg=theme["bg"])
        apply_theme_to_widget(window, theme)
        window.update_idletasks()

    clock_label = tk.Label(window, fg=theme["fg"], bg=theme["bg"], font=("Consolas", 12))
    clock_label.place(relx=1.0, rely=0.0, anchor='ne')

    def update_clock():
        clock_label.config(text=datetime.now().strftime("%A %Y-%m-%d %H:%M:%S"))
        window.after(1000, update_clock)
    update_clock()

    notebook = ttk.Notebook(window)
    notebook.pack(fill='both', expand=True)

    style = ttk.Style()
    style.theme_use('default')
    style.configure('TNotebook', background=theme["bg"])
    style.configure('TNotebook.Tab', background=theme["accent"], foreground=theme["fg"])
    style.map("TNotebook.Tab", background=[("selected", theme["button"])])
    style.configure('TFrame', background=theme["bg"])

    access_tab = tk.Frame(notebook, bg=theme["bg"])
    logs_tab = tk.Frame(notebook, bg=theme["bg"])
    config_tab = tk.Frame(notebook, bg=theme["bg"])
    wifi_tab = tk.Frame(notebook, bg=theme["bg"])

    notebook.add(access_tab, text='Access Panel')
    notebook.add(logs_tab, text='Access Logs')
    notebook.add(config_tab, text='Config Editor')
    notebook.add(wifi_tab, text='Wi-Fi Settings')

    def center_content(tab):
        frame = tk.Frame(tab, bg=theme["bg"])
        frame.place(relx=0.5, rely=0.5, anchor='center')
        return frame

    access_frame = center_content(access_tab)
    logs_frame = center_content(logs_tab)
    config_frame = center_content(config_tab)
    wifi_frame = center_content(wifi_tab)

    # ACCESS PANEL
    tk.Button(access_frame, text="Simulate RFID Scan", command=lambda: simulate_scan("12345678"),
              bg=theme["button"], fg=theme["fg"]).pack(pady=5)
    tk.Button(access_frame, text="Admin Override", command=lambda: messagebox.showinfo("Override", "Admin override"),
              bg=theme["button"], fg=theme["fg"]).pack(pady=5)

    def simulate_scan(uid):
        frame_img = get_mock_frame()
        snapshot_path = take_mock_snapshot(uid, frame_img)
        status = "granted" if uid in users else "denied"
        name = users.get(uid, {}).get("name", "Unknown")
        if is_blackout(config) and not users.get(uid, {}).get("admin", False):
            status = "denied (blackout)"
        log_access(uid, name, status, snapshot_path)
        messagebox.showinfo("Scan Result", f"UID: {uid}\nName: {name}\nAccess: {status}")

    # LOGS TAB
    log_list = tk.Text(logs_frame, wrap=tk.NONE, height=25, width=100, bg=theme["bg"], fg=theme["fg"])
    log_list.pack(padx=10, pady=10)

    def refresh_logs():
        log_list.delete('1.0', tk.END)
        for entry in load_logs():
            log_list.insert(tk.END, f"{entry['timestamp']} | {entry['uid']} | {entry['name']} | {entry['status']}\n")

    tk.Button(logs_frame, text="Refresh Logs", command=refresh_logs, bg=theme["button"], fg=theme["fg"]).pack()
    tk.Button(logs_frame, text="Export to CSV", command=export_logs_to_csv, bg=theme["button"], fg=theme["fg"]).pack()

    # CONFIG TAB
    tk.Label(config_frame, text="Admin PIN:", bg=theme["bg"], fg=theme["fg"]).grid(row=0, column=0, sticky='e', padx=5)
    admin_pin_entry = tk.Entry(config_frame, show="*", bg=theme["accent"], fg=theme["fg"])
    admin_pin_entry.insert(0, config.get("admin_pin", ""))
    admin_pin_entry.grid(row=0, column=1, columnspan=5, sticky='w')

    theme_var = tk.StringVar(value=config.get("theme_mode", "system"))
    tk.Label(config_frame, text="Theme Mode:", bg=theme["bg"], fg=theme["fg"]).grid(row=1, column=0, sticky='e')
    for i, mode in enumerate(["day", "night", "system"]):
        tk.Radiobutton(config_frame, text=mode.capitalize(), variable=theme_var, value=mode,
                       command=reload_theme, bg=theme["bg"], fg=theme["fg"],
                       activebackground=theme["accent"], selectcolor=theme["accent"]).grid(row=1, column=i+1)

    tk.Button(config_frame, text="Save Configuration", command=lambda: save_config_ui(),
              bg=theme["button"], fg=theme["fg"]).grid(row=3, column=0, columnspan=6, pady=10)

    def save_config_ui():
        config["admin_pin"] = admin_pin_entry.get()
        config["theme_mode"] = theme_var.get()
        save_config(config)
        reload_theme()
        messagebox.showinfo("Config", "Configuration saved.")

    # WIFI TAB
    wifi_config = load_wifi_config()

    tk.Label(wifi_frame, text="Current SSID:", bg=theme["bg"], fg=theme["fg"]).pack(pady=(10, 0))
    current_ssid_label = tk.Label(wifi_frame, text=wifi_config.get("ssid", ""), bg=theme["bg"], fg=theme["fg"])
    current_ssid_label.pack()

    tk.Label(wifi_frame, text="New SSID:", bg=theme["bg"], fg=theme["fg"]).pack(pady=(10, 0))
    ssid_entry = tk.Entry(wifi_frame, bg=theme["accent"], fg=theme["fg"])
    ssid_entry.insert(0, wifi_config.get("ssid", ""))
    ssid_entry.pack()

    tk.Label(wifi_frame, text="Wi-Fi Password:", bg=theme["bg"], fg=theme["fg"]).pack(pady=(10, 0))
    password_entry = tk.Entry(wifi_frame, bg=theme["accent"], fg=theme["fg"])
    password_entry.insert(0, wifi_config.get("password", ""))
    password_entry.pack()

    def save_and_connect_wifi():
        ssid = ssid_entry.get().strip()
        password = password_entry.get().strip()
        save_wifi_config(ssid, password)
        if write_to_wpa_supplicant(ssid, password):
            restart_wifi()
            current_ssid_label.config(text=ssid)
            messagebox.showinfo("Wi-Fi Updated", "Wi-Fi configuration applied.")
        else:
            messagebox.showerror("Permission Error", "Failed to write Wi-Fi config. Try running with sudo.")

    tk.Button(wifi_frame, text="Save & Connect", command=save_and_connect_wifi,
              bg=theme["button"], fg=theme["fg"]).pack(pady=10)

    apply_theme_to_widget(window, theme)
    window.mainloop()
