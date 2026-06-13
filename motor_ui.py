#!/usr/bin/env python3
"""
BLDC Motor Test UI
Sends SimpleFOC Commander 'M<value>' commands over serial.
Run: python3 motor_ui.py
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import threading
import time


class MotorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("BLDC Motor Controller")
        self.root.resizable(True, True)
        self.ser = None
        self.running = False
        self.last_cmd = None
        self._build()

    # ------------------------------------------------------------------ UI build
    def _build(self):
        # ---- Connection row ----
        cf = ttk.LabelFrame(self.root, text="Connection")
        cf.pack(fill="x", padx=10, pady=(8, 4))

        ttk.Label(cf, text="Port:").pack(side="left", padx=(8, 2))
        self.port_var = tk.StringVar(value="/dev/ttyUSB1")
        ttk.Entry(cf, textvariable=self.port_var, width=18).pack(side="left", padx=2)

        ttk.Label(cf, text="Baud:").pack(side="left", padx=(8, 2))
        self.baud_var = tk.StringVar(value="115200")
        ttk.Entry(cf, textvariable=self.baud_var, width=8).pack(side="left", padx=2)

        self.conn_btn = ttk.Button(cf, text="Connect", command=self._toggle_connect, width=12)
        self.conn_btn.pack(side="left", padx=8)

        self.status_var = tk.StringVar(value="Disconnected")
        self.status_lbl = ttk.Label(cf, textvariable=self.status_var, foreground="red", width=14)
        self.status_lbl.pack(side="left")

        # ---- Velocity slider ----
        sf = ttk.LabelFrame(self.root, text="Velocity")
        sf.pack(fill="x", padx=10, pady=4)

        self.vel_var = tk.DoubleVar(value=0.0)
        self.vel_var.trace_add("write", self._on_var_change)
        self.slider = ttk.Scale(sf, from_=-50, to=50, orient="horizontal",
                                variable=self.vel_var, length=480)
        self.slider.pack(padx=12, pady=(6, 2))

        self.vel_lbl = ttk.Label(sf, text="0.0 rad/s", font=("Courier", 18, "bold"))
        self.vel_lbl.pack(pady=(0, 4))

        # ---- Quick-set buttons ----
        qf = ttk.Frame(sf)
        qf.pack(pady=(0, 8))
        for v in [-30, -20, -10, -5]:
            ttk.Button(qf, text=f"{v}", width=5,
                       command=lambda x=v: self._set_vel(x)).pack(side="left", padx=2)
        ttk.Button(qf, text="STOP", width=6, style="Accent.TButton",
                   command=lambda: self._set_vel(0)).pack(side="left", padx=6)
        for v in [5, 10, 20, 30]:
            ttk.Button(qf, text=f"+{v}", width=5,
                       command=lambda x=v: self._set_vel(x)).pack(side="left", padx=2)

        # ---- Manual command entry ----
        mf = ttk.LabelFrame(self.root, text="Manual Command")
        mf.pack(fill="x", padx=10, pady=4)

        self.cmd_var = tk.StringVar()
        cmd_entry = ttk.Entry(mf, textvariable=self.cmd_var, width=30, font=("Courier", 11))
        cmd_entry.pack(side="left", padx=8, pady=6)
        cmd_entry.bind("<Return>", self._send_manual)
        ttk.Button(mf, text="Send", command=self._send_manual).pack(side="left", padx=4)
        ttk.Label(mf, text="e.g.  MVP0.2  MVI3  ML4  MD",
                  foreground="gray").pack(side="left", padx=10)

        # ---- Serial log ----
        lf = ttk.LabelFrame(self.root, text="Serial Log")
        lf.pack(fill="both", expand=True, padx=10, pady=(4, 8))

        self.log = scrolledtext.ScrolledText(lf, height=12, state="disabled",
                                             font=("Courier", 9), bg="#1e1e1e", fg="#d4d4d4")
        self.log.pack(fill="both", expand=True, padx=4, pady=4)

        btn_row = ttk.Frame(lf)
        btn_row.pack(anchor="e", padx=4, pady=(0, 4))
        ttk.Button(btn_row, text="Clear log", command=self._clear_log).pack()

    # ------------------------------------------------------------------ serial
    def _toggle_connect(self):
        if self.ser and self.ser.is_open:
            self.running = False
            time.sleep(0.1)
            self.ser.close()
            self.conn_btn.config(text="Connect")
            self.status_var.set("Disconnected")
            self.status_lbl.config(foreground="red")
            self._log("Disconnected.")
        else:
            try:
                self.ser = serial.Serial(self.port_var.get(),
                                         int(self.baud_var.get()), timeout=0.1)
                self.running = True
                threading.Thread(target=self._read_loop, daemon=True).start()
                self.conn_btn.config(text="Disconnect")
                self.status_var.set("Connected")
                self.status_lbl.config(foreground="green")
                self._log(f"Connected: {self.port_var.get()} @ {self.baud_var.get()}")
            except Exception as e:
                self._log(f"ERROR: {e}")

    def _read_loop(self):
        while self.running:
            try:
                line = self.ser.readline().decode("utf-8", errors="replace").rstrip()
                if line:
                    self.root.after(0, self._log, line)
            except Exception:
                pass

    def _send(self, cmd: str):
        if self.ser and self.ser.is_open:
            if cmd != self.last_cmd:
                self.ser.write((cmd + "\n").encode())
                self.last_cmd = cmd
                self._log(f">> {cmd}")

    # ------------------------------------------------------------------ controls
    def _on_var_change(self, *_):
        try:
            v = round(self.vel_var.get(), 1)
        except tk.TclError:
            return
        if abs(v) < 0.5:
            v = 0.0
        self.vel_lbl.config(text=f"{v:+.1f} rad/s")
        self._send(f"M{v}")

    def _set_vel(self, v):
        self.vel_var.set(float(v))

    def _send_manual(self, _event=None):
        cmd = self.cmd_var.get().strip()
        if cmd:
            self._send(cmd)
            self.cmd_var.set("")

    # ------------------------------------------------------------------ log
    def _log(self, msg: str):
        self.log.config(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}] {msg}\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = MotorUI(root)
    root.mainloop()
