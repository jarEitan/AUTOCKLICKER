"""
AutoClicker simple para Windows.
- Sin dependencias externas (solo librería estándar + ctypes).
- Hace clic donde esté el cursor.
- Hotkey global para iniciar/detener (por defecto F6).
"""
import ctypes
import threading
import time
import tkinter as tk
from tkinter import ttk

user32 = ctypes.windll.user32
try:
    ctypes.windll.winmm.timeBeginPeriod(1)  # mejora la precisión de los timers
except Exception:
    pass

# Flags de mouse_event
BUTTONS = {
    "Izquierdo": (0x0002, 0x0004),
    "Derecho": (0x0008, 0x0010),
    "Medio": (0x0020, 0x0040),
}
HOTKEYS = {f"F{i}": 0x70 + i - 1 for i in range(1, 13)}


def click(button, double=False):
    down, up = BUTTONS[button]
    for _ in range(2 if double else 1):
        user32.mouse_event(down, 0, 0, 0, 0)
        user32.mouse_event(up, 0, 0, 0, 0)


class App:
    def __init__(self, root):
        self.root = root
        root.title("AutoClicker")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        self.running = False
        self.stop_event = threading.Event()
        self.thread = None
        self.key_was_down = False

        pad = {"padx": 8, "pady": 4}
        main = ttk.Frame(root, padding=10)
        main.grid()

        # --- Intervalo ---
        f_int = ttk.LabelFrame(main, text="Intervalo entre clics")
        f_int.grid(row=0, column=0, sticky="ew", **pad)
        self.h = tk.StringVar(value="0")
        self.m = tk.StringVar(value="0")
        self.s = tk.StringVar(value="0")
        self.ms = tk.StringVar(value="100")
        for i, (var, label, mx) in enumerate(
            [(self.h, "h", 99), (self.m, "min", 59), (self.s, "s", 59), (self.ms, "ms", 999)]
        ):
            ttk.Spinbox(f_int, from_=0, to=mx, width=4, textvariable=var).grid(row=0, column=i * 2, padx=(8, 2), pady=6)
            ttk.Label(f_int, text=label).grid(row=0, column=i * 2 + 1, padx=(0, 4))

        # --- Opciones de clic ---
        f_opt = ttk.LabelFrame(main, text="Opciones de clic")
        f_opt.grid(row=1, column=0, sticky="ew", **pad)
        ttk.Label(f_opt, text="Botón:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.button = tk.StringVar(value="Izquierdo")
        ttk.Combobox(f_opt, textvariable=self.button, values=list(BUTTONS), state="readonly", width=12).grid(row=0, column=1, padx=8)
        ttk.Label(f_opt, text="Tipo:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.ctype = tk.StringVar(value="Simple")
        ttk.Combobox(f_opt, textvariable=self.ctype, values=["Simple", "Doble"], state="readonly", width=12).grid(row=1, column=1, padx=8)

        # --- Repetición ---
        f_rep = ttk.LabelFrame(main, text="Repetir")
        f_rep.grid(row=2, column=0, sticky="ew", **pad)
        self.rep_mode = tk.StringVar(value="inf")
        ttk.Radiobutton(f_rep, text="Hasta que lo detenga", variable=self.rep_mode, value="inf").grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=2)
        ttk.Radiobutton(f_rep, text="Cantidad:", variable=self.rep_mode, value="n").grid(row=1, column=0, sticky="w", padx=8, pady=2)
        self.count = tk.StringVar(value="100")
        ttk.Spinbox(f_rep, from_=1, to=9999999, width=8, textvariable=self.count).grid(row=1, column=1, padx=4)
        ttk.Label(f_rep, text="clics").grid(row=1, column=2, sticky="w")

        # --- Hotkey ---
        f_key = ttk.LabelFrame(main, text="Atajo de teclado (iniciar / detener)")
        f_key.grid(row=3, column=0, sticky="ew", **pad)
        self.hotkey = tk.StringVar(value="F6")
        ttk.Combobox(f_key, textvariable=self.hotkey, values=list(HOTKEYS), state="readonly", width=6).grid(row=0, column=0, padx=8, pady=6)
        ttk.Label(f_key, text="Funciona aunque la ventana no esté en foco").grid(row=0, column=1, padx=4)

        # --- Botón y estado ---
        self.btn = ttk.Button(main, text="Iniciar (F6)", command=self.toggle)
        self.btn.grid(row=4, column=0, sticky="ew", **pad)
        self.status = ttk.Label(main, text="Detenido", foreground="gray")
        self.status.grid(row=5, column=0, pady=(2, 0))

        self.hotkey.trace_add("write", lambda *_: self.update_button())
        self.poll_hotkey()

    # ---------- lógica ----------
    def interval(self):
        def n(v):
            try:
                return max(0, int(v.get()))
            except ValueError:
                return 0
        total = n(self.h) * 3600 + n(self.m) * 60 + n(self.s) + n(self.ms) / 1000
        return max(total, 0.001)

    def update_button(self):
        label = "Detener" if self.running else "Iniciar"
        self.btn.config(text=f"{label} ({self.hotkey.get()})")

    def toggle(self):
        self.stop() if self.running else self.start()

    def start(self):
        if self.running:
            return
        interval = self.interval()
        limit = None
        if self.rep_mode.get() == "n":
            try:
                limit = max(1, int(self.count.get()))
            except ValueError:
                limit = 1
        button = self.button.get()
        double = self.ctype.get() == "Doble"

        self.running = True
        self.stop_event.clear()
        self.update_button()
        self.status.config(text="Haciendo clics...", foreground="green")
        self.thread = threading.Thread(target=self.worker, args=(interval, limit, button, double), daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.running = False
        self.update_button()
        self.status.config(text="Detenido", foreground="gray")

    def worker(self, interval, limit, button, double):
        done = 0
        nxt = time.perf_counter()
        while not self.stop_event.is_set():
            click(button, double)
            done += 1
            if limit and done >= limit:
                break
            nxt += interval
            delay = nxt - time.perf_counter()
            if delay > 0:
                self.stop_event.wait(delay)
            else:
                nxt = time.perf_counter()
        if not self.stop_event.is_set():
            self.root.after(0, self.stop)  # terminó por cantidad

    def poll_hotkey(self):
        vk = HOTKEYS[self.hotkey.get()]
        down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
        if down and not self.key_was_down:
            self.toggle()
        self.key_was_down = down
        self.root.after(25, self.poll_hotkey)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
