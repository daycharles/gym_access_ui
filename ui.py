import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
import socket
import json
import threading
from PIL import Image, ImageTk
from storage import load_config, save_config, load_logs, export_logs_to_csv, load_users

# Always Night Theme
theme = {"bg": "#294856", "fg": "#ffffff", "accent": "#3a3a3a"}
monitor_events = []
TCP_PORT = 5005


def load_and_resize_image(path, size):
    img = Image.open(path)
    img = img.resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def make_icon_button(parent, image, command):
    btn = tk.Label(parent, image=image, bg=theme["bg"], cursor="hand2")
    btn.bind("<Button-1>", lambda e: command())
    btn.bind("<Enter>", lambda e: btn.config(bg=theme["accent"]))
    btn.bind("<Leave>", lambda e: btn.config(bg=theme["bg"]))
    btn.pack(side="left", padx=20, pady=10)
    return btn


def start_tcp_listener(update_callback):
    def listen():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", TCP_PORT))
        s.listen()
        while True:
            conn, _ = s.accept()
            with conn:
                try:
                    data = conn.recv(1024).decode()
                    if data:
                        evt = json.loads(data)
                        evt["timestamp"] = datetime.now().strftime("%H:%M:%S")
                        monitor_events.append(evt)
                        update_callback()
                except Exception as e:
                    print("[TCP] Error:", e)

    threading.Thread(target=listen, daemon=True).start()


def run_ui():
    config = load_config()
    root = tk.Tk()
    root.title("GateWise Main Station")
    root.geometry("1024x600")
    root.attributes("-fullscreen", True)
    root.configure(bg=theme["bg"])

    def prompt_pin():
        pin = ""
        pad = tk.Toplevel(root)
        pad.title("Enter Admin PIN")
        pad.geometry("300x500")
        pad.transient(root)  # float above main window
        pad.grab_set()  # make modal
        pad.lift()  # ensure it’s on top

        display_var = tk.StringVar(value="")
        tk.Label(pad, textvariable=display_var, font=("Arial", 24),
                 bg=theme["bg"], fg=theme["fg"]) \
            .pack(pady=20)

        def update_display():
            display_var.set("●" * len(pin))

        def on_digit(d):
            nonlocal pin
            if len(pin) < 6:
                pin += str(d)
                update_display()

        def on_clear():
            nonlocal pin
            pin = ""
            update_display()

        def on_back():
            nonlocal pin
            pin = pin[:-1]
            update_display()

        def on_enter(event=None):
            if pin == config.get("admin_pin", ""):
                pad.destroy()
                show_frame("settings")
            else:
                messagebox.showerror("Denied", "Incorrect PIN")
                on_clear()

        # Numeric keypad
        btn_frame = tk.Frame(pad, bg=theme["bg"])
        btn_frame.pack(expand=True)
        keys = [
            ("1", 1), ("2", 2), ("3", 3),
            ("4", 4), ("5", 5), ("6", 6),
            ("7", 7), ("8", 8), ("9", 9),
            ("←", "back"), ("0", 0), ("C", "clear")
        ]
        for idx, (txt, val) in enumerate(keys):
            cmd = (lambda v=val: on_back() if v == "back"
            else on_clear() if v == "clear"
            else on_digit(v))
            tk.Button(btn_frame, text=txt, font=("Arial", 18),
                      width=4, height=2, command=cmd) \
                .grid(row=idx // 3, column=idx % 3, padx=5, pady=5)

        # ENTER button
        enter_btn = tk.Button(pad, text="Enter", font=("Arial", 18),
                              bg=theme["accent"], fg=theme["fg"],
                              width=12, command=on_enter)
        enter_btn.pack(pady=10)
        pad.bind("<Return>", on_enter)

        pad.wait_window()

    def open_settings():
        prompt_pin()

    # Load icons
    icons = {}
    icon_files = [
        ("logo", "assets/icons/Gatewise.PNG"),
        ("logs", "assets/icons/logs-white.png"),
        ("config", "assets/icons/config_white.png"),
        ("lock", "assets/icons/lock_white.png"),
        ("unlock", "assets/icons/unlock_white.png"),
        ("unlock_class", "assets/icons/unlock_for_class.png"),
        ("back", "assets/icons/back_white.png"),
        ("minimize", "assets/icons/minimize_white.png"),
        ("blackout", "assets/icons/blackout_white.png"),
        ("users", "assets/icons/users.png"),
        ("refresh", "assets/icons/refresh_white.png"),
        ("export", "assets/icons/export_white.png"),
        ("save", "assets/icons/save_white.png"),
    ]
    for name, path in icon_files:
        size = (120, 120) if name == "logo" else (80, 80)
        icons[name] = load_and_resize_image(path, size)

    # Create frames
    frames = {}
    for name in ["home", "logs", "settings", "blackout", "users", "admin"]:
        f = tk.Frame(root, bg=theme["bg"])
        f.place(relx=0.5, rely=0.5, anchor="center", relwidth=1, relheight=1)
        frames[name] = f
        # clock on each
        clk = tk.Label(f, font=("Arial", 14), fg=theme["fg"], bg=theme["bg"])
        clk.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

        def tick(lbl=clk):
            lbl.config(text=datetime.now().strftime("%m-%d-%Y %H:%M"))
            lbl.after(1000, lambda: tick(lbl))

        tick()

    def show_frame(name):
        frames[name].tkraise()

    # Bottom bar helper
    def bottom_bar(frame, extras=None, show_back=True, back_location="home"):
        bar = tk.Frame(frame, bg=theme["bg"])
        bar.pack(side="bottom", fill="x", pady=5)
        # common buttons
        make_icon_button(bar, icons["lock"], lambda: messagebox.showinfo("Action", "Lock sent"))
        make_icon_button(bar, icons["unlock"], lambda: messagebox.showinfo("Action", "Unlock sent"))
        make_icon_button(bar, icons["unlock_class"], lambda:
        messagebox.showinfo("Action",
                            f"Class unlock {config.get('unlock_class_duration', 15)}m"))
        # page-specific extras
        if extras:
            for text, cmd, img in extras:
                make_icon_button(bar, img, cmd)
        # back
        if show_back:
            back_btn = tk.Label(bar, image=icons["back"], bg=theme["bg"], cursor="hand2")
            back_btn.bind("<Button-1>", lambda e: show_frame(back_location))
            back_btn.pack(side="right", padx=20)
        return bar

    # --- Home ---
    home = frames["home"]
    tk.Label(home, image=icons["logo"], bg=theme["bg"]).pack(pady=30)
    menu = tk.Frame(home, bg=theme["bg"]);
    menu.pack(expand=True)
    make_icon_button(menu, icons["logs"], lambda: show_frame("logs"))
    make_icon_button(menu, icons["config"], open_settings)
    bottom_bar(home, show_back=False)

    # --- Logs ---
    logs_f = frames["logs"]
    tk.Label(logs_f, text="Live Door Monitor", font=("Helvetica", 18),
             bg=theme["bg"], fg=theme["fg"]).pack(pady=10)
    log_text = tk.Text(logs_f, bg=theme["bg"], fg=theme["fg"],
                       state="disabled", width=100, height=20)
    log_text.pack(pady=5)

    def update_logs():
        log_text.config(state="normal");
        log_text.delete("1.0", tk.END)
        for e in reversed(monitor_events[-100:]):
            log_text.insert(tk.END,
                            f"{e['timestamp']} | Door:{e.get('door', '-')} | UID:{e.get('uid', '-')} | Status:{e.get('status', '-')}\n")
        log_text.config(state="disabled")

    refresh_cmd = ("Refresh", update_logs, icons["refresh"])
    bottom_bar(logs_f, extras=[refresh_cmd, ("Export", lambda: export_logs_to_csv(), icons["export"])])

    # --- Settings ---
    st = frames["settings"]
    tk.Label(st, text="Settings", font=("Helvetica", 18),
             bg=theme["bg"], fg=theme["fg"]).place(relx=0.5, rely=0.1, anchor="n")
    icons_frame = tk.Frame(st, bg=theme["bg"])
    icons_frame.place(relx=0.5, rely=0.4, anchor="center", relwidth=1, relheight=0.4)
    left = tk.Frame(icons_frame, bg=theme["bg"])
    left.place(relx=0.25, rely=0.5, anchor="center")
    make_icon_button(left, icons["blackout"], lambda: show_frame("blackout"))
    right = tk.Frame(icons_frame, bg=theme["bg"])
    right.place(relx=0.75, rely=0.5, anchor="center")
    make_icon_button(right, icons["users"], lambda: show_frame("users"))

    df = tk.Frame(st, bg=theme["bg"]);
    df.place(relx=0.5, rely=0.75, anchor="center")
    tk.Label(df, text="Unlock-for-Class (min):", font=("Arial", 14),
             bg=theme["bg"], fg=theme["fg"]).pack(side="left")
    increments = [str(i) for i in range(15, 181, 15)]
    uc = tk.StringVar(value=str(config.get("unlock_class_duration", 15)))
    ttk.Combobox(df, textvariable=uc, state="readonly", width=4,
                 values=increments).pack(side="left", padx=5)

    def save_settings():
        try:
            dur = int(uc.get())
            config["unlock_class_duration"] = dur
            save_config(config)
            messagebox.showinfo("Saved", f"Duration set to {dur}s.")
        except ValueError:
            messagebox.showerror("Error", "Invalid number.")

    save_cmd = ("Save", save_settings, icons["save"])
    minimize_cmd = ("Minimize", lambda: root.attributes("-fullscreen", False), icons["minimize"])
    bottom_bar(st, extras=[save_cmd, minimize_cmd])

    # --- Blackout Schedule ---
    bo = frames["blackout"]
    tk.Label(bo, text="Blackout Schedule", font=("Helvetica", 16),
             bg=theme["bg"], fg=theme["fg"]).pack(pady=10)
    bo_top = tk.Frame(bo, bg=theme["bg"]);
    bo_top.pack(fill="both", expand=True)
    bo_bot = tk.Frame(bo, bg=theme["bg"]);
    bo_bot.pack(fill="x")
    tk.Label(bo_top, text="Advanced Blackout Schedule",
             font=("Helvetica", 20, "bold"), bg=theme["bg"], fg=theme["fg"]).pack(pady=10)
    scroll_canvas = tk.Canvas(bo_top, bg=theme["bg"], highlightthickness=0)
    h_scroll = tk.Scrollbar(bo_top, orient="horizontal", command=scroll_canvas.xview)
    scroll_canvas.configure(xscrollcommand=h_scroll.set)
    scroll_canvas.pack(side="top", fill="both", expand=True, padx=10)
    h_scroll.pack(side="bottom", fill="x")
    scroll_frame = tk.Frame(scroll_canvas, bg=theme["bg"])
    scroll_canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    scroll_frame.bind("<Configure>", lambda e:
    scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
    blackout_settings = config.get("blackout", {})
    day_block_widgets = {}

    def add_block_ui(day_frame, day, blk=None):
        row = tk.Frame(day_frame, bg=theme["bg"]);
        row.pack(pady=4, padx=5, anchor="w")
        s = blk["start"] if blk else 0;
        e = blk["end"] if blk else 1
        sv = tk.StringVar(value=f"{s:02d}:00");
        ev = tk.StringVar(value=f"{e:02d}:00")
        times = [f"{h:02d}:00" for h in range(24)]
        style = {"font": ("Arial", 11), "width": 6, "state": "readonly"}
        ttk.Combobox(row, textvariable=sv, values=times, **style).pack(side="left", padx=2)
        tk.Label(row, text="→", bg=theme["bg"], fg=theme["fg"]).pack(side="left")
        ttk.Combobox(row, textvariable=ev, values=times, **style).pack(side="left", padx=2)
        tk.Button(row, text="✕", bg="#c0392b", fg="white", width=3,
                  command=row.destroy).pack(side="left", padx=6)
        day_block_widgets[day].append((sv, ev))

    def create_day_column(day):
        frm = tk.LabelFrame(scroll_frame, text=day,
                            font=("Arial", 14, "bold"),
                            bg=theme["bg"], fg=theme["fg"], padx=8, pady=5)
        frm.pack(side="left", padx=10, pady=10)
        day_block_widgets[day] = []
        for blk in blackout_settings.get(day, []):
            add_block_ui(frm, day, blk)
        tk.Button(frm, text="+ Add Block", bg=theme["accent"], fg=theme["fg"],
                  command=lambda d=day, f=frm: add_block_ui(f, d),
                  relief="groove").pack(anchor="w", pady=5)

    for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        create_day_column(d)

    def save_blackout():
        updated = {}
        for d, blocks in day_block_widgets.items():
            updated[d] = [
                {"start": int(sv.get().split(":")[0]), "end": int(ev.get().split(":")[0])}
                for sv, ev in blocks
            ]
        config["blackout"] = updated
        save_config(config)
        messagebox.showinfo("Saved", "Blackout schedule saved.")

    save_bo_cmd = ("Save", save_blackout, icons["save"])
    bottom_bar(bo, extras=[save_bo_cmd, ], back_location="settings")

    # --- User Maintenance ---
    um = frames["users"]
    tk.Label(um, text="User Maintenance", font=("Helvetica", 16),
             bg=theme["bg"], fg=theme["fg"]).pack(pady=10)
    cols = ("UID", "Name", "Admin")
    tv = ttk.Treeview(um, columns=cols, show="headings", height=8)
    for c in cols: tv.heading(c, text=c)
    tv.pack(pady=5)
    for uid, data in load_users().items():
        tv.insert("", tk.END, values=(uid, data["name"], data.get("admin", False)))
    push_cmd = ("Push", lambda: messagebox.showinfo("Push", "Users pushed"), icons["config"])
    bottom_bar(um, extras=[push_cmd], back_location="settings")

    # --- Admin Panel (if still needed) ---
    # ... similarly attach bottom_bar(admin_tab, extras=[...]) ...

    # Start listener & initial update
    start_tcp_listener(update_logs)
    show_frame("home")
    root.mainloop()
