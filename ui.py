import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import camera
from camera import get_mock_frame, take_mock_snapshot
from storage import save_config, log_access, load_users, load_config, is_blackout
from datetime import datetime

DAY_THEME = {
    "bg": "#f0f0f0",
    "fg": "#000000",
    "accent": "#cccccc",
    "button": "#e0e0e0"
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

        # Root window and top-level widgets
        window.configure(bg=theme["bg"])
        clock_label.configure(bg=theme["bg"], fg=theme["fg"])

        # ttk notebook + tab styles
        style.configure('TNotebook', background=theme["bg"], borderwidth=0)
        style.configure('TNotebook.Tab', background=theme["accent"], foreground=theme["fg"])
        style.map('TNotebook.Tab', background=[("selected", theme["button"])])
        style.configure('TFrame', background=theme["bg"])  # for tab content areas

        # Tab frame backgrounds (inside Notebook)
        for tab in [access_tab, logs_tab, config_tab]:
            tab.configure(bg=theme["bg"])

        # Inner frames (centered content blocks)
        for frame in [access_frame, logs_frame, config_frame]:
            frame.configure(bg=theme["bg"])

        # Apply theme recursively to all children
        apply_theme_to_widget(window, theme)

        window.update_idletasks()

    # Clock
    clock_label = tk.Label(window, fg=theme["fg"], bg=theme["bg"], font=("Consolas", 12))
    clock_label.place(relx=1.0, rely=0.0, anchor='ne')

    def update_clock():
        clock_label.config(text=datetime.now().strftime("%A %Y-%m-%d %H:%M:%S"))
        window.after(1000, update_clock)

    update_clock()

    # Notebook Tabs
    notebook = ttk.Notebook(window)
    notebook.pack(fill='both', expand=True)

    style = ttk.Style()
    style.theme_use('default')
    style.configure('TNotebook', background=theme["bg"])
    style.configure('TNotebook.Tab', background=theme["accent"], foreground=theme["fg"])
    style.map("TNotebook.Tab", background=[("selected", theme["button"])])

    access_tab = tk.Frame(notebook, bg=theme["bg"])
    logs_tab = tk.Frame(notebook, bg=theme["bg"])
    config_tab = tk.Frame(notebook, bg=theme["bg"])

    notebook.add(access_tab, text='Access Panel')
    notebook.add(logs_tab, text='Access Logs')
    notebook.add(config_tab, text='Config Editor')

    # Centering helpers
    def center_content(tab):
        frame = tk.Frame(tab, bg=theme["bg"])
        frame.place(relx=0.5, rely=0.5, anchor='center')
        return frame

    # ACCESS PANEL
    access_frame = center_content(access_tab)
    cam_label = tk.Label(access_frame, text="Camera Feed (mock)", bg="black", fg="white", width=80, height=15)
    cam_label.pack(pady=10)

    def simulate_scan(uid="12345678"):
        frame_img = camera.get_mock_frame()
        snapshot_path = take_mock_snapshot(uid, frame_img)
        status = "denied"
        name = "Unknown"

        if uid in users:
            user = users[uid]
            name = user["name"]
            if is_blackout(config) and not user.get("admin"):
                status = "denied (blackout)"
            else:
                status = "granted"
        log_access(uid, name, status, snapshot_path)
        messagebox.showinfo("Scan Result", f"UID: {uid}\nName: {name}\nAccess: {status}")

    def admin_override():
        pin = simpledialog.askstring("Admin Override", "Enter admin PIN:", show="*")
        if pin == config.get("admin_pin"):
            messagebox.showinfo("Override", "Access granted (admin override)")
        else:
            messagebox.showerror("Error", "Invalid PIN")

    tk.Button(access_frame, text="Simulate RFID Scan", command=simulate_scan,
              bg=theme["button"], fg=theme["fg"]).pack(pady=5)
    tk.Button(access_frame, text="Admin Override", command=admin_override,
              bg=theme["button"], fg=theme["fg"]).pack(pady=5)

    # LOGS TAB
    logs_frame = center_content(logs_tab)
    log_list = tk.Text(logs_frame, wrap=tk.NONE, height=25, width=100,
                       bg=theme["bg"], fg=theme["fg"])
    log_list.pack(padx=10, pady=10)

    def refresh_logs():
        log_list.delete('1.0', tk.END)
        for entry in load_logs():
            log_list.insert(tk.END, f"{entry['timestamp']} | {entry['uid']} | {entry['name']} | {entry['status']}\n")

    def export_logs():
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if file_path:
            export_logs_to_csv(file_path)
            messagebox.showinfo("Export", "Logs exported successfully.")

    tk.Button(logs_frame, text="Refresh Logs", command=refresh_logs,
              bg=theme["button"], fg=theme["fg"]).pack()
    tk.Button(logs_frame, text="Export to CSV", command=export_logs,
              bg=theme["button"], fg=theme["fg"]).pack(pady=5)

    # CONFIG TAB
    config_frame = center_content(config_tab)
    tk.Label(config_frame, text="Admin PIN:", bg=theme["bg"], fg=theme["fg"]).grid(row=0, column=0, sticky='e', padx=5, pady=5)
    admin_pin_entry = tk.Entry(config_frame, show="*", bg=theme["accent"], fg=theme["fg"])
    admin_pin_entry.insert(0, config.get("admin_pin", ""))
    admin_pin_entry.grid(row=0, column=1, columnspan=25, sticky='w', pady=5)

    # Theme selector
    theme_var = tk.StringVar(value=config.get("theme_mode", "system"))
    tk.Label(config_frame, text="Theme Mode:", bg=theme["bg"], fg=theme["fg"]).grid(row=1, column=0, sticky='e', padx=5)
    for i, mode in enumerate(["day", "night", "system"]):
        tk.Radiobutton(config_frame, text=mode.capitalize(), variable=theme_var, value=mode,
                       command=reload_theme, bg=theme["bg"], fg=theme["fg"],
                       activebackground=theme["accent"], selectcolor=theme["accent"]).grid(row=1, column=i+1)

    # Save button
    def save_config_ui():
        config["admin_pin"] = admin_pin_entry.get()
        config["theme_mode"] = theme_var.get()
        save_config(config)
        reload_theme()
        messagebox.showinfo("Config", "Configuration saved.")

    tk.Button(config_frame, text="Save Configuration", command=save_config_ui,
              bg=theme["button"], fg=theme["fg"]).grid(row=3, column=0, columnspan=10, pady=10)

    apply_theme_to_widget(window, theme)

    window.mainloop()
