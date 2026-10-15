import os
import sys
import ctypes
from ctypes import wintypes
import threading
import winsound
import tkinter as tk
from tkinter import ttk

# Global handle to prevent garbage collection of Windows Job Object
GLOBAL_JOB_HANDLE = None

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

def apply_resource_limits(max_cpu_percent=20, max_ram_mb=256):
    """
    Enforces hard OS-level limits using Windows Job Object:
    - CPU limit: max_cpu_percent (hard cap via JobObjectCpuRateControlInformation)
    - RAM limit: max_ram_mb (ProcessMemoryLimit & JobMemoryLimit)
    - Process priority: BELOW_NORMAL_PRIORITY_CLASS
    """
    global GLOBAL_JOB_HANDLE
    if sys.platform != "win32":
        return "Не Windows (лимиты пропущены)"

    status_msgs = []
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        # 1. Lower process priority so the app never interferes with other tasks
        kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), 0x00004000)

        # 2. Windows Job Object setup
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.SetInformationJobObject.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        )

        hJob = kernel32.CreateJobObjectW(None, None)
        if not hJob:
            return f"Ошибка CreateJobObject: {ctypes.get_last_error()}"

        GLOBAL_JOB_HANDLE = hJob

        # 3. Configure 256 MB RAM limit
        JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
        JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        mem_bytes = max_ram_mb * 1024 * 1024
        ext_limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        ext_limits.BasicLimitInformation.LimitFlags = (
            JOB_OBJECT_LIMIT_PROCESS_MEMORY | JOB_OBJECT_LIMIT_JOB_MEMORY
        )
        ext_limits.ProcessMemoryLimit = mem_bytes
        ext_limits.JobMemoryLimit = mem_bytes

        ret_mem = kernel32.SetInformationJobObject(
            hJob, 9, ctypes.byref(ext_limits), ctypes.sizeof(ext_limits)
        )
        if ret_mem:
            status_msgs.append(f"ОЗУ <= {max_ram_mb}МБ")

        # 4. Configure CPU Rate hard cap (20%)
        JOB_OBJECT_CPU_RATE_CONTROL_ENABLE = 0x1
        JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP = 0x4

        class JOBOBJECT_CPU_RATE_CONTROL_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("ControlFlags", wintypes.DWORD),
                ("CpuRate", wintypes.DWORD),  # cycles per 10,000 (20% = 2000)
            ]

        cpu_limits = JOBOBJECT_CPU_RATE_CONTROL_INFORMATION()
        cpu_limits.ControlFlags = (
            JOB_OBJECT_CPU_RATE_CONTROL_ENABLE | JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP
        )
        cpu_limits.CpuRate = int(max_cpu_percent * 100)

        ret_cpu = kernel32.SetInformationJobObject(
            hJob, 15, ctypes.byref(cpu_limits), ctypes.sizeof(cpu_limits)
        )
        if ret_cpu:
            status_msgs.append(f"CPU <= {max_cpu_percent}%")

        # 5. Assign current process to Job Object
        hProc = kernel32.GetCurrentProcess()
        ret_assign = kernel32.AssignProcessToJobObject(hJob, hProc)
        if not ret_assign:
            status_msgs.append(f"(вложенный Job: {ctypes.get_last_error()})")

        return " + ".join(status_msgs) if status_msgs else "Лимиты установлены"
    except Exception as e:
        return f"Лимиты частично активны: {e}"


# --- Small Caps & Monospace Mappings ---
LATIN_TO_SMALL = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ꜰ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ꞯ', 'r': 'ʀ', 's': 'ꜱ', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ'
}

CYRILLIC_TO_SMALL = {
    'а': 'ᴀ', 'б': 'ᴃ', 'в': 'ʙ', 'г': 'ᴦ', 'д': 'ᴅ', 'е': 'ᴇ', 'ё': 'ᴇ̈',
    'ж': 'ж', 'з': 'ᴢ', 'и': 'ᴎ', 'й': 'ᴎ̆', 'к': 'ᴋ', 'л': 'ᴫ', 'м': 'ᴍ',
    'н': 'ʜ', 'о': 'ᴏ', 'п': 'ᴨ', 'р': 'ᴘ', 'с': 'ᴄ', 'т': 'ᴛ', 'у': 'ʏ',
    'ф': 'ф', 'х': 'х', 'ц': 'ц', 'ч': 'ч', 'ш': 'ш', 'щ': 'щ', 'ъ': 'ъ',
    'ы': 'ы', 'ь': 'ь', 'э': 'э', 'ю': 'ю', 'я': 'ᴙ',
    'і': 'ɪ', 'ї': 'ɪ̈', 'є': 'ᴇ', 'ў': 'ʏ̆', 'ґ': 'ᴦ'
}

# Reverse Small Caps
SMALL_TO_NORMAL = {
    'ᴀ': 'а', 'ᴃ': 'б', 'ʙ': 'в', 'ᴦ': 'г', 'ᴅ': 'д', 'ᴇ': 'е', 'ᴇ̈': 'ё',
    'ᴢ': 'з', 'ᴎ': 'и', 'ᴎ̆': 'й', 'ᴋ': 'к', 'ᴫ': 'л', 'ᴍ': 'м', 'ʜ': 'н',
    'ᴏ': 'о', 'ᴨ': 'п', 'ᴘ': 'р', 'ᴄ': 'с', 'ᴛ': 'т', 'ʏ': 'у', 'ᴙ': 'я',
    'ꜰ': 'f', 'ɢ': 'g', 'ɪ': 'i', 'ᴊ': 'j', 'ʟ': 'l', 'ɴ': 'n', 'ꞯ': 'q',
    'ʀ': 'r', 'ꜱ': 's', 'ᴜ': 'u', 'ᴠ': 'v', 'ᴡ': 'w'
}

def to_small_caps(text: str) -> tuple[str, str, str]:
    if not text.strip():
        return "", "Готов к вводу (RU / EN)", "#a1a1aa"

    cyr_count = 0
    lat_count = 0
    small_count = 0

    for ch in text:
        low = ch.lower()
        if '\u0400' <= low <= '\u04ff' and low not in (' ', '\n', '\t'):
            cyr_count += 1
        elif 'a' <= low <= 'z':
            lat_count += 1
        elif ch in SMALL_TO_NORMAL:
            small_count += 1

    # Check if input is predominantly small caps (reverse mode)
    if small_count > 0 and small_count >= (cyr_count + lat_count):
        res = [SMALL_TO_NORMAL.get(ch, ch) for ch in text]
        return "".join(res), "Авто: Small Caps -> Обычный", "#38bdf8"

    res = []
    for ch in text:
        low = ch.lower()
        if ('\u0400' <= low <= '\u04ff') or low in CYRILLIC_TO_SMALL:
            res.append(CYRILLIC_TO_SMALL.get(low, ch))
        elif ('a' <= low <= 'z') or low in LATIN_TO_SMALL:
            res.append(LATIN_TO_SMALL.get(low, ch))
        else:
            res.append(ch)

    if cyr_count > 0 and lat_count > 0:
        label = "Авто: Смешанный (RU + EN) -> Small Caps"
        color = "#a78bfa"
    elif cyr_count > 0:
        label = "Авто: Кириллица (RU) -> Small Caps"
        color = "#38bdf8"
    elif lat_count > 0:
        label = "Авто: Английский (EN) -> Small Caps"
        color = "#34d399"
    else:
        label = "Авто: Текст -> Small Caps"
        color = "#94a3b8"

    return "".join(res), label, color

def to_fullwidth_mono(text: str) -> tuple[str, str, str]:
    if not text.strip():
        return "", "Готов к вводу (Широкий)", "#a1a1aa"

    # Check reverse fullwidth
    is_fw = any(0xFF01 <= ord(c) <= 0xFF5E for c in text)
    if is_fw:
        res = []
        for c in text:
            code = ord(c)
            if 0xFF01 <= code <= 0xFF5E:
                res.append(chr(code - 0xFEE0))
            elif code == 0x3000:
                res.append(' ')
            else:
                res.append(c)
        return "".join(res), "Авто: Широкий -> Обычный", "#38bdf8"

    res = []
    for c in text:
        code = ord(c)
        # Latin & basic symbols -> Fullwidth (0xFF01 - 0xFF5E)
        if 0x21 <= code <= 0x7E:
            res.append(chr(code + 0xFEE0))
        elif code == 0x20:
            res.append('  ')
        # Cyrillic wide formatting
        elif ('\u0400' <= c <= '\u04ff'):
            res.append(c + ' ')
        else:
            res.append(c)

    return "".join(res).strip(), "Широкий Моноширинный (Wide)", "#f59e0b"

def convert_by_style(text: str, style: str) -> tuple[str, str, str]:
    if style == "wide":
        return to_fullwidth_mono(text)
    return to_small_caps(text)


def get_current_ram_mb():
    try:
        class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        kernel32.K32GetProcessMemoryInfo.restype = wintypes.BOOL

        pmc = PROCESS_MEMORY_COUNTERS_EX()
        pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
        hProc = kernel32.GetCurrentProcess()
        if kernel32.K32GetProcessMemoryInfo(hProc, ctypes.byref(pmc), pmc.cb):
            return round(pmc.WorkingSetSize / (1024 * 1024), 1)
    except Exception:
        pass
    return None


class HotkeyListener(threading.Thread):
    def __init__(self, on_hotkey_convert, on_hotkey_toggle):
        super().__init__(daemon=True)
        self.on_hotkey_convert = on_hotkey_convert
        self.on_hotkey_toggle = on_hotkey_toggle
        self.thread_id = None
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    def run(self):
        self.thread_id = self.kernel32.GetCurrentThreadId()
        # Hotkey 1: Ctrl + Alt + S (convert clipboard on the fly)
        # Hotkey 2: Ctrl + Alt + W (toggle window show/hide)
        MOD_ALT = 0x0001
        MOD_CONTROL = 0x0002
        self.user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT, ord('S'))
        self.user32.RegisterHotKey(None, 2, MOD_CONTROL | MOD_ALT, ord('W'))

        msg = wintypes.MSG()
        while True:
            res = self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res <= 0:
                break
            if msg.message == 0x0312: # WM_HOTKEY
                if msg.wParam == 1 and self.on_hotkey_convert:
                    self.on_hotkey_convert()
                elif msg.wParam == 2 and self.on_hotkey_toggle:
                    self.on_hotkey_toggle()
            self.user32.TranslateMessage(ctypes.byref(msg))
            self.user32.DispatchMessageW(ctypes.byref(msg))

        self.user32.UnregisterHotKey(None, 1)
        self.user32.UnregisterHotKey(None, 2)

    def stop(self):
        if self.thread_id:
            self.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0) # WM_QUIT


class SmallCapsApp:
    def __init__(self, root: tk.Tk, limit_info: str):
        self.root = root
        self.root.title("Small Caps Converter")
        self.root.geometry("560x590")
        self.root.minsize(480, 500)
        self.limit_info = limit_info

        self.is_topmost = False
        self.current_style = "smallcaps"  # "smallcaps" or "wide"
        self.history = []  # last 8 items

        # Dark theme palette
        self.bg_color = "#18181b"       # Main background
        self.card_color = "#27272a"     # Card surface
        self.input_bg = "#121214"       # Textarea background
        self.text_color = "#f4f4f5"     # Primary text
        self.text_dim = "#a1a1aa"       # Dimmed text
        self.accent_blue = "#2563eb"    # Action button
        self.accent_hover = "#1d4ed8"   # Hover state
        self.success_color = "#10b981"  # Copied state
        self.border_color = "#3f3f46"   # Border

        self.root.configure(bg=self.bg_color)

        # Set window icon
        icon_path = get_resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self._build_ui()
        self._update_ram_counter()

        # Handle window close: hide to tray/background instead of exit
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Start global hotkeys
        self.hotkey_listener = HotkeyListener(
            on_hotkey_convert=lambda: self.root.after(0, self.on_global_hotkey_convert),
            on_hotkey_toggle=lambda: self.root.after(0, self.toggle_window)
        )
        self.hotkey_listener.start()

    def _build_ui(self):
        container = tk.Frame(self.root, bg=self.bg_color, padx=14, pady=10)
        container.pack(fill=tk.BOTH, expand=True)

        # Header Frame: Title, Always-On-Top, Style Selector, Auto-Badge
        header_frame = tk.Frame(container, bg=self.bg_color)
        header_frame.pack(fill=tk.X, pady=(0, 6))

        title_lbl = tk.Label(
            header_frame,
            text="Small Caps & Wide",
            font=("Segoe UI", 12, "bold"),
            fg=self.text_color,
            bg=self.bg_color,
        )
        title_lbl.pack(side=tk.LEFT)

        # Always on top pin button
        self.btn_topmost = tk.Button(
            header_frame,
            text="📌 Закрепить",
            command=self.toggle_always_on_top,
            bg=self.card_color,
            fg=self.text_dim,
            activebackground="#3f3f46",
            activeforeground="#ffffff",
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            pady=2,
        )
        self.btn_topmost.pack(side=tk.LEFT, padx=(10, 0))

        # Dynamic Auto-detection badge
        self.badge_detected = tk.Label(
            header_frame,
            text="⚡ Готов к вводу",
            font=("Segoe UI", 8, "bold"),
            fg=self.text_dim,
            bg=self.card_color,
            padx=8,
            pady=2,
        )
        self.badge_detected.pack(side=tk.RIGHT)

        # Style switch bar
        style_bar = tk.Frame(container, bg=self.card_color, padx=4, pady=3)
        style_bar.pack(fill=tk.X, pady=(0, 6))

        lbl_style = tk.Label(
            style_bar,
            text="Стиль:",
            font=("Segoe UI", 8, "bold"),
            fg=self.text_dim,
            bg=self.card_color,
        )
        lbl_style.pack(side=tk.LEFT, padx=(4, 6))

        self.btn_style_small = tk.Button(
            style_bar,
            text="ᴀʙᴄ Small Caps",
            command=lambda: self.set_style("smallcaps"),
            bg=self.accent_blue,
            fg="#ffffff",
            activebackground=self.accent_hover,
            activeforeground="#ffffff",
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=2,
        )
        self.btn_style_small.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_style_wide = tk.Button(
            style_bar,
            text="ＡＢＣ Широкий Моно",
            command=lambda: self.set_style("wide"),
            bg=self.card_color,
            fg=self.text_dim,
            activebackground="#3f3f46",
            activeforeground="#ffffff",
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=2,
        )
        self.btn_style_wide.pack(side=tk.LEFT)

        # Hotkey tip label
        hotkey_tip = tk.Label(
            style_bar,
            text="Хоткей: Ctrl+Alt+S (буфер) | Ctrl+Alt+W (окно)",
            font=("Segoe UI", 8),
            fg="#71717a",
            bg=self.card_color,
        )
        hotkey_tip.pack(side=tk.RIGHT, padx=(0, 4))

        # Input Section
        in_lbl_frame = tk.Frame(container, bg=self.bg_color)
        in_lbl_frame.pack(fill=tk.X, pady=(2, 2))

        in_lbl = tk.Label(
            in_lbl_frame,
            text="Исходный текст (RU / EN):",
            font=("Segoe UI", 9, "bold"),
            fg=self.text_dim,
            bg=self.bg_color,
        )
        in_lbl.pack(side=tk.LEFT)

        self.char_count_lbl = tk.Label(
            in_lbl_frame,
            text="0 симв.",
            font=("Segoe UI", 8),
            fg=self.text_dim,
            bg=self.bg_color,
        )
        self.char_count_lbl.pack(side=tk.RIGHT)

        in_frame = tk.Frame(container, bg=self.border_color, padx=1, pady=1)
        in_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.txt_input = tk.Text(
            in_frame,
            height=4,
            bg=self.input_bg,
            fg=self.text_color,
            insertbackground=self.text_color,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=8,
            pady=6,
            undo=True,
        )
        self.txt_input.pack(fill=tk.BOTH, expand=True)
        self.txt_input.focus_set()

        # Output Section
        out_lbl = tk.Label(
            container,
            text="Результат:",
            font=("Segoe UI", 9, "bold"),
            fg=self.text_dim,
            bg=self.bg_color,
            anchor="w",
        )
        out_lbl.pack(fill=tk.X, pady=(2, 2))

        out_frame = tk.Frame(container, bg=self.border_color, padx=1, pady=1)
        out_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.txt_output = tk.Text(
            out_frame,
            height=4,
            bg=self.input_bg,
            fg="#60a5fa",
            insertbackground=self.text_color,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=8,
            pady=6,
        )
        self.txt_output.pack(fill=tk.BOTH, expand=True)

        # Buttons Toolbar
        btn_frame = tk.Frame(container, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=(0, 6))

        self.btn_copy = tk.Button(
            btn_frame,
            text="📋 Скопировать одной кнопкой",
            command=self.copy_to_clipboard,
            bg=self.accent_blue,
            fg="#ffffff",
            activebackground=self.accent_hover,
            activeforeground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=14,
            pady=6,
        )
        self.btn_copy.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.btn_clear = tk.Button(
            btn_frame,
            text="✕ Очистить",
            command=self.clear_fields,
            bg=self.card_color,
            fg=self.text_dim,
            activebackground="#3f3f46",
            activeforeground=self.text_color,
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=6,
        )
        self.btn_clear.pack(side=tk.RIGHT)

        # History Section (Last 8 items)
        hist_header = tk.Frame(container, bg=self.bg_color)
        hist_header.pack(fill=tk.X, pady=(2, 2))

        lbl_hist = tk.Label(
            hist_header,
            text="История последних записей:",
            font=("Segoe UI", 8, "bold"),
            fg=self.text_dim,
            bg=self.bg_color,
        )
        lbl_hist.pack(side=tk.LEFT)

        btn_clear_hist = tk.Button(
            hist_header,
            text="Очистить историю",
            command=self.clear_history,
            font=("Segoe UI", 7),
            fg="#71717a",
            bg=self.bg_color,
            activebackground=self.card_color,
            activeforeground=self.text_dim,
            relief=tk.FLAT,
            cursor="hand2",
            bd=0,
        )
        btn_clear_hist.pack(side=tk.RIGHT)

        self.hist_container = tk.Frame(container, bg=self.card_color, padx=4, pady=4)
        self.hist_container.pack(fill=tk.X, pady=(0, 6))

        self.lbl_hist_empty = tk.Label(
            self.hist_container,
            text="История пока пуста. Скопированный текст появится здесь в 1 клик.",
            font=("Segoe UI", 8),
            fg="#71717a",
            bg=self.card_color,
        )
        self.lbl_hist_empty.pack(fill=tk.X)

        # Status Bar / Limit Info & Exit Button
        status_frame = tk.Frame(container, bg=self.card_color, padx=8, pady=4)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_status = tk.Label(
            status_frame,
            text=f"Лимиты: {self.limit_info}",
            font=("Segoe UI", 8),
            fg="#a1a1aa",
            bg=self.card_color,
        )
        self.lbl_status.pack(side=tk.LEFT)

        btn_exit = tk.Button(
            status_frame,
            text="Выход",
            command=self.quit_app,
            font=("Segoe UI", 7),
            fg="#ef4444",
            bg=self.card_color,
            activebackground="#3f3f46",
            activeforeground="#f87171",
            relief=tk.FLAT,
            cursor="hand2",
            bd=0,
            padx=6,
        )
        btn_exit.pack(side=tk.RIGHT, padx=(6, 0))

        self.lbl_ram = tk.Label(
            status_frame,
            text="ОЗУ: ~12 МБ / 256 МБ",
            font=("Segoe UI", 8),
            fg="#4ade80",
            bg=self.card_color,
        )
        self.lbl_ram.pack(side=tk.RIGHT)

        # Keyboard shortcuts
        def select_all(event):
            event.widget.tag_add("sel", "1.0", "end")
            return "break"

        self.txt_input.bind("<Control-a>", select_all)
        self.txt_input.bind("<Control-A>", select_all)
        self.txt_output.bind("<Control-a>", select_all)
        self.txt_output.bind("<Control-A>", select_all)
        self.root.bind("<Control-Return>", lambda e: self.copy_to_clipboard())
        self.root.bind("<Escape>", lambda e: self.hide_window())
        self.root.bind("<Control-q>", lambda e: self.quit_app())

        # Real-time binding
        self.txt_input.bind("<KeyRelease>", lambda e: self.on_text_changed())
        self.txt_input.bind("<<Paste>>", lambda e: self.root.after(10, self.on_text_changed))
        self.txt_input.bind("<Control-v>", lambda e: self.root.after(10, self.on_text_changed))

    def set_style(self, style: str):
        self.current_style = style
        if style == "smallcaps":
            self.btn_style_small.config(bg=self.accent_blue, fg="#ffffff", font=("Segoe UI", 8, "bold"))
            self.btn_style_wide.config(bg=self.card_color, fg=self.text_dim, font=("Segoe UI", 8))
        else:
            self.btn_style_wide.config(bg=self.accent_blue, fg="#ffffff", font=("Segoe UI", 8, "bold"))
            self.btn_style_small.config(bg=self.card_color, fg=self.text_dim, font=("Segoe UI", 8))
        self.on_text_changed()

    def toggle_always_on_top(self):
        self.is_topmost = not self.is_topmost
        self.root.attributes("-topmost", self.is_topmost)
        if self.is_topmost:
            self.btn_topmost.config(text="📌 Закреплено", bg=self.accent_blue, fg="#ffffff")
        else:
            self.btn_topmost.config(text="📌 Закрепить", bg=self.card_color, fg=self.text_dim)

    def on_text_changed(self):
        raw_text = self.txt_input.get("1.0", tk.END)
        if raw_text.endswith("\n"):
            raw_text = raw_text[:-1]

        char_count = len(raw_text)
        self.char_count_lbl.config(text=f"{char_count} симв.")

        converted, label, tag_color = convert_by_style(raw_text, self.current_style)
        self.badge_detected.config(text=f"⚡ {label}", fg=tag_color)

        self.txt_output.delete("1.0", tk.END)
        self.txt_output.insert("1.0", converted)

    def copy_to_clipboard(self):
        text = self.txt_output.get("1.0", tk.END)
        if text.endswith("\n"):
            text = text[:-1]

        if not text.strip():
            self._flash_status("⚠ Поле пустое — нечего копировать", "#facc15")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()

        self.add_to_history(text)

        self.btn_copy.config(text="✓ Скопировано!", bg=self.success_color)
        self._flash_status("✓ Текст успешно скопирован в буфер обмена!", "#4ade80")
        self.root.after(1500, self._reset_copy_btn)

    def on_global_hotkey_convert(self):
        """Global Hotkey (Ctrl+Alt+S): grabs clipboard, transforms it on the fly, and beeps."""
        try:
            raw_text = self.root.clipboard_get()
        except Exception:
            return

        if not raw_text or not raw_text.strip():
            return

        converted, label, tag_color = convert_by_style(raw_text, self.current_style)
        if not converted:
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(converted)
        self.root.update()

        self.add_to_history(converted)

        # If window is visible, update UI
        if self.root.winfo_viewable():
            self.txt_input.delete("1.0", tk.END)
            self.txt_input.insert("1.0", raw_text)
            self.txt_output.delete("1.0", tk.END)
            self.txt_output.insert("1.0", converted)
            self.badge_detected.config(text=f"⚡ {label}", fg=tag_color)
            self._flash_status("✓ Буфер сконвертирован по хоткею (Ctrl+Alt+S)", "#4ade80")

        # Soft system chime
        try:
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass

    def add_to_history(self, item: str):
        cleaned = item.strip()
        if not cleaned:
            return
        if cleaned in self.history:
            self.history.remove(cleaned)
        self.history.insert(0, cleaned)
        if len(self.history) > 8:
            self.history = self.history[:8]
        self._render_history()

    def _render_history(self):
        for widget in self.hist_container.winfo_children():
            widget.destroy()

        if not self.history:
            self.lbl_hist_empty = tk.Label(
                self.hist_container,
                text="История пока пуста. Скопированный текст появится здесь в 1 клик.",
                font=("Segoe UI", 8),
                fg="#71717a",
                bg=self.card_color,
            )
            self.lbl_hist_empty.pack(fill=tk.X)
            return

        for text_val in self.history:
            preview = text_val.replace("\n", " ")
            if len(preview) > 45:
                preview = preview[:45] + "..."

            btn_item = tk.Button(
                self.hist_container,
                text=f"📋 {preview}",
                command=lambda val=text_val: self._use_history_item(val),
                bg="#18181b",
                fg=self.text_color,
                activebackground="#3f3f46",
                activeforeground="#ffffff",
                font=("Segoe UI", 8),
                relief=tk.FLAT,
                cursor="hand2",
                anchor="w",
                padx=8,
                pady=2,
            )
            btn_item.pack(fill=tk.X, pady=1)

    def _use_history_item(self, val: str):
        self.txt_output.delete("1.0", tk.END)
        self.txt_output.insert("1.0", val)
        self.root.clipboard_clear()
        self.root.clipboard_append(val)
        self.root.update()
        self._flash_status("✓ Скопировано из истории!", "#4ade80")

    def clear_history(self):
        self.history = []
        self._render_history()
        self._flash_status("История очищена", "#a1a1aa")

    def hide_window(self):
        self.root.withdraw()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def toggle_window(self):
        if self.root.winfo_viewable():
            self.hide_window()
        else:
            self.show_window()

    def _reset_copy_btn(self):
        self.btn_copy.config(text="📋 Скопировать одной кнопкой", bg=self.accent_blue)

    def _flash_status(self, msg: str, color: str):
        self.lbl_status.config(text=msg, fg=color)
        self.root.after(3000, self._restore_status)

    def _restore_status(self):
        self.lbl_status.config(text=f"Лимиты: {self.limit_info}", fg="#a1a1aa")

    def clear_fields(self):
        self.txt_input.delete("1.0", tk.END)
        self.txt_output.delete("1.0", tk.END)
        self.char_count_lbl.config(text="0 симв.")
        self.badge_detected.config(text="⚡ Готов к вводу", fg=self.text_dim)
        self.txt_input.focus_set()

    def _update_ram_counter(self):
        ram_mb = get_current_ram_mb()
        if ram_mb is not None:
            self.lbl_ram.config(text=f"ОЗУ: {ram_mb} МБ / 256 МБ")
        self.root.after(3000, self._update_ram_counter)

    def quit_app(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.root.destroy()


def main():
    limit_info = apply_resource_limits(max_cpu_percent=20, max_ram_mb=256)
    root = tk.Tk()
    app = SmallCapsApp(root, limit_info)
    root.mainloop()

if __name__ == "__main__":
    main()
