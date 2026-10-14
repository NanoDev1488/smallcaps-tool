import os
import sys
import ctypes
from ctypes import wintypes
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

        # 1. Lower process priority so the app never interferes with other tasks on a weak CPU
        # BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
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
        # JobObjectExtendedLimitInformation = 9
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
            status_msgs.append(f"ОЗУ ≤ {max_ram_mb}МБ")

        # 4. Configure CPU Rate hard cap (20%)
        # JobObjectCpuRateControlInformation = 15
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
            status_msgs.append(f"CPU ≤ {max_cpu_percent}%")

        # 5. Assign current process to Job Object
        hProc = kernel32.GetCurrentProcess()
        ret_assign = kernel32.AssignProcessToJobObject(hJob, hProc)
        if not ret_assign:
            status_msgs.append(f"(вложенный Job: {ctypes.get_last_error()})")

        return " + ".join(status_msgs) if status_msgs else "Лимиты установлены"
    except Exception as e:
        return f"Лимиты частично активны: {e}"


# Small Caps Mappings
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

# Reverse mapping: Small Caps -> Normal Cyrillic / Latin
SMALL_TO_NORMAL = {
    'ᴀ': 'а', 'ᴃ': 'б', 'ʙ': 'в', 'ᴦ': 'г', 'ᴅ': 'д', 'ᴇ': 'е', 'ᴇ̈': 'ё',
    'ᴢ': 'з', 'ᴎ': 'и', 'ᴎ̆': 'й', 'ᴋ': 'к', 'ᴫ': 'л', 'ᴍ': 'м', 'ʜ': 'н',
    'ᴏ': 'о', 'ᴨ': 'п', 'ᴘ': 'р', 'ᴄ': 'с', 'ᴛ': 'т', 'ʏ': 'у', 'ᴙ': 'я',
    'ꜰ': 'f', 'ɢ': 'g', 'ɪ': 'i', 'ᴊ': 'j', 'ʟ': 'l', 'ɴ': 'n', 'ꞯ': 'q',
    'ʀ': 'r', 'ꜱ': 's', 'ᴜ': 'u', 'ᴠ': 'v', 'ᴡ': 'w'
}

def auto_convert_text(text: str) -> tuple[str, str, str]:
    """
    Automatically detects input language (Cyrillic, Latin, Mixed, or Small Caps)
    and converts characters to the appropriate Small Caps representation.
    Returns: (converted_text, detection_label, tag_color)
    """
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
        return "".join(res), "Авто: Small Caps → Обычный", "#38bdf8"

    # Forward mode: convert regular text to small caps
    res = []
    for ch in text:
        low = ch.lower()
        # Russian/Cyrillic character
        if ('\u0400' <= low <= '\u04ff') or low in CYRILLIC_TO_SMALL:
            res.append(CYRILLIC_TO_SMALL.get(low, ch))
        # English/Latin character
        elif ('a' <= low <= 'z') or low in LATIN_TO_SMALL:
            res.append(LATIN_TO_SMALL.get(low, ch))
        else:
            res.append(ch)

    if cyr_count > 0 and lat_count > 0:
        label = "Авто: Смешанный (RU + EN) → Small Caps"
        color = "#a78bfa"  # Purple
    elif cyr_count > 0:
        label = "Авто: Кирилица (RU) → Small Caps"
        color = "#38bdf8"  # Cyan/Sky
    elif lat_count > 0:
        label = "Авто: Английский (EN) → Small Caps"
        color = "#34d399"  # Emerald
    else:
        label = "Авто: Текст → Small Caps"
        color = "#94a3b8"

    return "".join(res), label, color


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


class SmallCapsApp:
    def __init__(self, root: tk.Tk, limit_info: str):
        self.root = root
        self.root.title("Small Caps Converter")
        self.root.geometry("540x510")
        self.root.minsize(460, 420)
        self.limit_info = limit_info

        # Dark theme palette
        self.bg_color = "#18181b"       # Main background (zinc-900)
        self.card_color = "#27272a"     # Card surface (zinc-800)
        self.input_bg = "#121214"       # Textarea background
        self.text_color = "#f4f4f5"     # Primary text (zinc-100)
        self.text_dim = "#a1a1aa"       # Dimmed text (zinc-400)
        self.accent_blue = "#2563eb"    # Copy button (blue-600)
        self.accent_hover = "#1d4ed8"   # Hover state
        self.success_color = "#10b981"  # Copied state (emerald-500)
        self.border_color = "#3f3f46"   # Border (zinc-700)

        self.root.configure(bg=self.bg_color)

        # Set taskbar / window icon
        icon_path = get_resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self._build_ui()
        self._update_ram_counter()

    def _build_ui(self):
        # Main padding frame
        container = tk.Frame(self.root, bg=self.bg_color, padx=14, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        # Header with Title and Auto-detection Badge
        header_frame = tk.Frame(container, bg=self.bg_color)
        header_frame.pack(fill=tk.X, pady=(0, 6))

        title_lbl = tk.Label(
            header_frame,
            text="Small Caps Генератор",
            font=("Segoe UI", 12, "bold"),
            fg=self.text_color,
            bg=self.bg_color,
        )
        title_lbl.pack(side=tk.LEFT)

        # Dynamic Auto-detection badge
        self.badge_detected = tk.Label(
            header_frame,
            text="⚡ Готов к вводу (RU / EN)",
            font=("Segoe UI", 9, "bold"),
            fg=self.text_dim,
            bg=self.card_color,
            padx=10,
            pady=3,
        )
        self.badge_detected.pack(side=tk.RIGHT)

        # Input Section
        in_lbl_frame = tk.Frame(container, bg=self.bg_color)
        in_lbl_frame.pack(fill=tk.X, pady=(4, 2))

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

        # Input Text Area
        in_frame = tk.Frame(container, bg=self.border_color, padx=1, pady=1)
        in_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.txt_input = tk.Text(
            in_frame,
            height=5,
            bg=self.input_bg,
            fg=self.text_color,
            insertbackground=self.text_color,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=8,
            pady=8,
            undo=True,
        )
        self.txt_input.pack(fill=tk.BOTH, expand=True)
        self.txt_input.focus_set()

        # Output Section
        out_lbl = tk.Label(
            container,
            text="Результат (Small Caps):",
            font=("Segoe UI", 9, "bold"),
            fg=self.text_dim,
            bg=self.bg_color,
            anchor="w",
        )
        out_lbl.pack(fill=tk.X, pady=(4, 2))

        out_frame = tk.Frame(container, bg=self.border_color, padx=1, pady=1)
        out_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.txt_output = tk.Text(
            out_frame,
            height=5,
            bg=self.input_bg,
            fg="#60a5fa",  # Highlighted result color
            insertbackground=self.text_color,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=8,
            pady=8,
        )
        self.txt_output.pack(fill=tk.BOTH, expand=True)

        # Button Toolbar
        btn_frame = tk.Frame(container, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=(0, 6))

        # Big Copy Button
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
            padx=16,
            pady=7,
        )
        self.btn_copy.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        # Clear Button
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
            pady=7,
        )
        self.btn_clear.pack(side=tk.RIGHT)

        # Status Bar / Limit Info
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

        self.lbl_ram = tk.Label(
            status_frame,
            text="ОЗУ: ~15 МБ / 256 МБ",
            font=("Segoe UI", 8),
            fg="#4ade80",
            bg=self.card_color,
        )
        self.lbl_ram.pack(side=tk.RIGHT)

        # Keyboard shortcuts (Ctrl+A select all, Ctrl+Return copy)
        def select_all(event):
            event.widget.tag_add("sel", "1.0", "end")
            return "break"

        self.txt_input.bind("<Control-a>", select_all)
        self.txt_input.bind("<Control-A>", select_all)
        self.txt_output.bind("<Control-a>", select_all)
        self.txt_output.bind("<Control-A>", select_all)
        self.root.bind("<Control-Return>", lambda e: self.copy_to_clipboard())

        # Real-time binding
        self.txt_input.bind("<KeyRelease>", lambda e: self.on_text_changed())
        self.txt_input.bind("<<Paste>>", lambda e: self.root.after(10, self.on_text_changed))
        self.txt_input.bind("<Control-v>", lambda e: self.root.after(10, self.on_text_changed))

    def on_text_changed(self):
        raw_text = self.txt_input.get("1.0", tk.END)
        # Tkinter adds a trailing \n by default
        if raw_text.endswith("\n"):
            raw_text = raw_text[:-1]

        char_count = len(raw_text)
        self.char_count_lbl.config(text=f"{char_count} симв.")

        converted, label, tag_color = auto_convert_text(raw_text)
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

        # Visual feedback on button and status bar
        self.btn_copy.config(text="✓ Скопировано!", bg=self.success_color)
        self._flash_status("✓ Текст успешно скопирован в буфер обмена!", "#4ade80")
        self.root.after(1500, self._reset_copy_btn)

    def _reset_copy_btn(self):
        self.btn_copy.config(
            text="📋 Скопировать одной кнопкой", bg=self.accent_blue
        )

    def _flash_status(self, msg: str, color: str):
        self.lbl_status.config(text=msg, fg=color)
        self.root.after(3000, self._restore_status)

    def _restore_status(self):
        self.lbl_status.config(
            text=f"Лимиты: {self.limit_info}", fg="#a1a1aa"
        )

    def clear_fields(self):
        self.txt_input.delete("1.0", tk.END)
        self.txt_output.delete("1.0", tk.END)
        self.char_count_lbl.config(text="0 симв.")
        self.badge_detected.config(text="⚡ Готов к вводу (RU / EN)", fg=self.text_dim)
        self.txt_input.focus_set()

    def _update_ram_counter(self):
        ram_mb = get_current_ram_mb()
        if ram_mb is not None:
            self.lbl_ram.config(text=f"ОЗУ: {ram_mb} МБ / 256 МБ")
        # Update every 3 seconds without loading CPU
        self.root.after(3000, self._update_ram_counter)


def main():
    # Enforce 20% CPU and 256MB RAM Job Object limits before GUI initialization
    limit_info = apply_resource_limits(max_cpu_percent=20, max_ram_mb=256)

    root = tk.Tk()
    app = SmallCapsApp(root, limit_info)
    root.mainloop()


if __name__ == "__main__":
    main()
