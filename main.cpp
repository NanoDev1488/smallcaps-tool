#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN

#include <windows.h>
#include <windowsx.h>
#include <commctrl.h>
#include <shellapi.h>
#include <psapi.h>
#include <dwmapi.h>
#include <string>
#include <vector>
#include <unordered_map>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "psapi.lib")
#pragma comment(lib, "dwmapi.lib")
#pragma comment(lib, "comctl32.lib")

#define WM_TRAYICON (WM_USER + 101)
#define IDI_APP_ICON 101

#define IDC_INPUT_TEXT   1001
#define IDC_OUTPUT_TEXT  1002
#define IDC_BTN_COPY     1003
#define IDC_BTN_CLEAR    1004
#define IDC_BTN_TOPMOST  1005
#define IDC_BTN_STYLE_SC 1006
#define IDC_BTN_STYLE_WD 1007
#define IDC_STATUS_LABEL 1008
#define IDC_RAM_LABEL    1009
#define IDC_BADGE_LABEL  1010
#define IDC_HIST_BTN_BASE 2000

#define IDM_TRAY_RESTORE 3001
#define IDM_TRAY_EXIT    3002

// Global UI Handles
HWND g_hWnd = NULL;
HWND g_hEditIn = NULL;
HWND g_hEditOut = NULL;
HWND g_hBtnCopy = NULL;
HWND g_hBtnClear = NULL;
HWND g_hBtnTopmost = NULL;
HWND g_hBtnStyleSC = NULL;
HWND g_hBtnStyleWD = NULL;
HWND g_hLblStatus = NULL;
HWND g_hLblRam = NULL;
HWND g_hLblBadge = NULL;
std::vector<HWND> g_histButtons;

NOTIFYICONDATAW g_nid = { 0 };
bool g_isTopmost = false;
bool g_isWideMode = false;
std::vector<std::wstring> g_history;

// Color Palette (Dark Theme matching Python Tkinter palette)
COLORREF COLOR_BG          = RGB(24, 24, 27);     // #18181b Main background
COLORREF COLOR_CARD        = RGB(39, 39, 42);     // #27272a Card surface
COLORREF COLOR_CARD_HOVER  = RGB(63, 63, 70);     // #3f3f46 Hover state
COLORREF COLOR_BORDER      = RGB(63, 63, 70);     // #3f3f46 Border
COLORREF COLOR_INPUT_BG    = RGB(18, 18, 20);     // #121214 Textarea background
COLORREF COLOR_TEXT        = RGB(244, 244, 245);  // #f4f4f5 Primary text
COLORREF COLOR_TEXT_DIM    = RGB(161, 161, 170);  // #a1a1aa Dimmed text
COLORREF COLOR_ACCENT      = RGB(37, 99, 235);    // #2563eb Primary blue
COLORREF COLOR_ACCENT_HOVER= RGB(29, 78, 216);    // #1d4ed8 Primary blue hover
COLORREF COLOR_GREEN       = RGB(16, 185, 129);   // #10b981 Success green
COLORREF COLOR_GREEN_DARK  = RGB(20, 83, 45);     // #14532d Success green bg

HBRUSH g_brBg = NULL;
HBRUSH g_brCard = NULL;
HBRUSH g_brInput = NULL;
HFONT g_hFontUI = NULL;
HFONT g_hFontBold = NULL;
HFONT g_hFontSmall = NULL;

HANDLE g_hJob = NULL;

// Enforce 20% CPU rate hard cap and 256MB RAM hard limit
void ApplyResourceLimits() {
    SetPriorityClass(GetCurrentProcess(), BELOW_NORMAL_PRIORITY_CLASS);

    g_hJob = CreateJobObjectW(NULL, NULL);
    if (!g_hJob) return;

    JOBOBJECT_EXTENDED_LIMIT_INFORMATION extLimits = { 0 };
    extLimits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY | JOB_OBJECT_LIMIT_JOB_MEMORY;
    extLimits.ProcessMemoryLimit = 256 * 1024 * 1024;
    extLimits.JobMemoryLimit = 256 * 1024 * 1024;
    SetInformationJobObject(g_hJob, JobObjectExtendedLimitInformation, &extLimits, sizeof(extLimits));

    JOBOBJECT_CPU_RATE_CONTROL_INFORMATION cpuLimits = { 0 };
    cpuLimits.ControlFlags = JOB_OBJECT_CPU_RATE_CONTROL_ENABLE | JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP;
    cpuLimits.CpuRate = 2000; // 20%
    SetInformationJobObject(g_hJob, JobObjectCpuRateControlInformation, &cpuLimits, sizeof(cpuLimits));

    AssignProcessToJobObject(g_hJob, GetCurrentProcess());
}

// Memory Release on Minimizing to Tray
void FreeProcessMemory() {
    // 1. Release working set back to OS
    EmptyWorkingSet(GetCurrentProcess());
    SetProcessWorkingSetSize(GetCurrentProcess(), (SIZE_T)-1, (SIZE_T)-1);
}

// Convert functions
std::wstring ToSmallCaps(const std::wstring& in, std::wstring& outBadge) {
    if (in.empty()) {
        outBadge = L"⚡ Готов к вводу";
        return L"";
    }

    static const std::unordered_map<wchar_t, std::wstring> cyrMap = {
        {L'а', L"ᴀ"}, {L'б', L"ᴃ"}, {L'в', L"ʙ"}, {L'г', L"ᴦ"}, {L'д', L"ᴅ"},
        {L'е', L"ᴇ"}, {L'ё', L"ᴇ̈"}, {L'ж', L"ж"}, {L'з', L"ᴢ"}, {L'и', L"ᴎ"},
        {L'й', L"ᴎ̆"}, {L'к', L"ᴋ"}, {L'л', L"ᴫ"}, {L'м', L"ᴍ"}, {L'н', L"ʜ"},
        {L'о', L"ᴏ"}, {L'п', L"ᴨ"}, {L'р', L"ᴘ"}, {L'с', L"ᴄ"}, {L'т', L"ᴛ"},
        {L'у', L"ʏ"}, {L'ф', L"ф"}, {L'х', L"х"}, {L'ц', L"ц"}, {L'ч', L"ч"},
        {L'ш', L"ш"}, {L'щ', L"щ"}, {L'ъ', L"ъ"}, {L'ы', L"ы"}, {L'ь', L"ь"},
        {L'э', L"э"}, {L'ю', L"ю"}, {L'я', L"ᴙ"}, {L'і', L"ɪ"}, {L'ї', L"ɪ̈"},
        {L'є', L"ᴇ"}, {L'ў', L"ʏ̆"}, {L'ґ', L"ᴦ"}
    };

    static const std::unordered_map<wchar_t, wchar_t> latMap = {
        {L'a', 0x1D00}, {L'b', 0x0299}, {L'c', 0x1D04}, {L'd', 0x1D05}, {L'e', 0x1D07},
        {L'f', 0xA730}, {L'g', 0x0262}, {L'h', 0x029C}, {L'i', 0x026A}, {L'j', 0x1D0A},
        {L'k', 0x1D0B}, {L'l', 0x029F}, {L'm', 0x1D0D}, {L'n', 0x0274}, {L'o', 0x1D0F},
        {L'p', 0x1D18}, {L'q', 0xA7AF}, {L'r', 0x0280}, {L's', 0xA731}, {L't', 0x1D1B},
        {L'u', 0x1D1C}, {L'v', 0x1D20}, {L'w', 0x1D21}, {L'x', L'x'},   {L'y', 0x028F},
        {L'z', 0x1D22}
    };

    static const std::unordered_map<wchar_t, wchar_t> revMap = {
        {0x1D00, L'а'}, {0x1D03, L'б'}, {0x0299, L'в'}, {0x1D26, L'г'}, {0x1D05, L'д'},
        {0x1D07, L'е'}, {0x1D22, L'з'}, {0x1D0E, L'и'}, {0x1D0B, L'к'}, {0x1D2B, L'л'},
        {0x1D0D, L'м'}, {0x029C, L'н'}, {0x1D0F, L'о'}, {0x1D28, L'п'}, {0x1D18, L'р'},
        {0x1D04, L'с'}, {0x1D1B, L'т'}, {0x028F, L'у'}, {0x1D19, L'я'}, {0xA730, L'f'},
        {0x0262, L'g'}, {0x026A, L'i'}, {0x1D0A, L'j'}, {0x029F, L'l'}, {0x0274, L'n'},
        {0xA7AF, L'q'}, {0x0280, L'r'}, {0xA731, L's'}, {0x1D1C, L'u'}, {0x1D20, L'v'},
        {0x1D21, L'w'}
    };

    int cyrCount = 0, latCount = 0, scCount = 0;
    for (wchar_t c : in) {
        wchar_t low = towlower(c);
        if (low >= 0x0400 && low <= 0x04FF) cyrCount++;
        else if (low >= L'a' && low <= L'z') latCount++;
        else if (revMap.find(c) != revMap.end()) scCount++;
    }

    // Check if input is predominantly small caps (Reverse mode)
    if (scCount > 0 && scCount >= (cyrCount + latCount)) {
        outBadge = L"⚡ Авто: Small Caps -> Обычный";
        std::wstring res = L"";
        for (wchar_t c : in) {
            auto it = revMap.find(c);
            res += (it != revMap.end()) ? it->second : c;
        }
        return res;
    }

    std::wstring res = L"";
    for (wchar_t c : in) {
        wchar_t low = towlower(c);
        auto itCyr = cyrMap.find(low);
        if (itCyr != cyrMap.end()) {
            res += itCyr->second;
        } else {
            auto itLat = latMap.find(low);
            if (itLat != latMap.end()) {
                res += itLat->second;
            } else {
                res += c;
            }
        }
    }

    if (cyrCount > 0 && latCount > 0) outBadge = L"⚡ Авто: Смешанный (RU+EN) -> Small Caps";
    else if (cyrCount > 0) outBadge = L"⚡ Авто: Кириллица -> Small Caps";
    else if (latCount > 0) outBadge = L"⚡ Авто: Английский -> Small Caps";
    else outBadge = L"⚡ Авто: Текст -> Small Caps";

    return res;
}

std::wstring ToWideMono(const std::wstring& in, std::wstring& outBadge) {
    if (in.empty()) {
        outBadge = L"⚡ Готов к вводу";
        return L"";
    }

    // Check reverse fullwidth
    bool hasFw = false;
    for (wchar_t c : in) {
        if (c >= 0xFF01 && c <= 0xFF5E) { hasFw = true; break; }
    }
    if (hasFw) {
        outBadge = L"⚡ Авто: Широкий -> Обычный";
        std::wstring res = L"";
        for (wchar_t c : in) {
            if (c >= 0xFF01 && c <= 0xFF5E) res += (wchar_t)(c - 0xFEE0);
            else if (c == 0x3000) res += L' ';
            else res += c;
        }
        return res;
    }

    outBadge = L"⚡ Широкий Моноширинный";
    std::wstring res = L"";
    for (wchar_t c : in) {
        if (c >= 0x0021 && c <= 0x007E) {
            res += (wchar_t)(c + 0xFEE0);
        } else if (c == L' ') {
            res += L"  ";
        } else if (c >= 0x0400 && c <= 0x04FF) {
            res += c;
            res += L' ';
        } else {
            res += c;
        }
    }
    return res;
}

void UpdateConversion();

void AddHistory(const std::wstring& text) {
    if (text.empty()) return;
    for (auto it = g_history.begin(); it != g_history.end(); ++it) {
        if (*it == text) {
            g_history.erase(it);
            break;
        }
    }
    g_history.insert(g_history.begin(), text);
    if (g_history.size() > 8) g_history.resize(8);

    // Refresh history UI buttons
    for (size_t i = 0; i < g_histButtons.size(); i++) {
        if (i < g_history.size()) {
            std::wstring prev = g_history[i];
            if (prev.length() > 40) prev = prev.substr(0, 40) + L"...";
            std::wstring label = L"📋  " + prev;
            SetWindowTextW(g_histButtons[i], label.c_str());
            ShowWindow(g_histButtons[i], SW_SHOW);
            InvalidateRect(g_histButtons[i], NULL, FALSE);
        } else {
            ShowWindow(g_histButtons[i], SW_HIDE);
        }
    }
}

void CopyToClipboard(const std::wstring& text) {
    if (text.empty()) return;
    if (!OpenClipboard(g_hWnd)) return;
    EmptyClipboard();
    size_t bytes = (text.length() + 1) * sizeof(wchar_t);
    HGLOBAL hMem = GlobalAlloc(GMEM_MOVEABLE, bytes);
    if (hMem) {
        memcpy(GlobalLock(hMem), text.c_str(), bytes);
        GlobalUnlock(hMem);
        SetClipboardData(CF_UNICODETEXT, hMem);
    }
    CloseClipboard();

    AddHistory(text);

    SetWindowTextW(g_hBtnCopy, L"✓ Скопировано в буфер!");
    InvalidateRect(g_hBtnCopy, NULL, FALSE);
    SetTimer(g_hWnd, 1, 1500, NULL);
}

void OnGlobalHotkeyConvert() {
    if (!OpenClipboard(NULL)) return;
    HANDLE hData = GetClipboardData(CF_UNICODETEXT);
    if (!hData) {
        CloseClipboard();
        return;
    }
    wchar_t* pText = (wchar_t*)GlobalLock(hData);
    std::wstring text = pText ? pText : L"";
    GlobalUnlock(hData);
    CloseClipboard();

    if (text.empty()) return;

    std::wstring badge;
    std::wstring converted = g_isWideMode ? ToWideMono(text, badge) : ToSmallCaps(text, badge);
    if (converted.empty()) return;

    CopyToClipboard(converted);
    MessageBeep(MB_OK);

    if (IsWindowVisible(g_hWnd)) {
        SetWindowTextW(g_hEditIn, text.c_str());
        SetWindowTextW(g_hEditOut, converted.c_str());
        SetWindowTextW(g_hLblBadge, badge.c_str());
    }
}

void ShowAppWindow() {
    ShowWindow(g_hWnd, SW_RESTORE);
    SetForegroundWindow(g_hWnd);
}

void HideAppWindow() {
    ShowWindow(g_hWnd, SW_HIDE);
    // Release working set when minimized to tray
    FreeProcessMemory();
}

void ToggleAppWindow() {
    if (IsWindowVisible(g_hWnd)) {
        HideAppWindow();
    } else {
        ShowAppWindow();
    }
}

void UpdateConversion() {
    int len = GetWindowTextLengthW(g_hEditIn);
    std::wstring inText(len, L'\0');
    GetWindowTextW(g_hEditIn, &inText[0], len + 1);

    std::wstring badge;
    std::wstring outText = g_isWideMode ? ToWideMono(inText, badge) : ToSmallCaps(inText, badge);

    SetWindowTextW(g_hEditOut, outText.c_str());
    SetWindowTextW(g_hLblBadge, badge.c_str());
}

void UpdateRamCounter() {
    PROCESS_MEMORY_COUNTERS_EX pmc = { 0 };
    pmc.cb = sizeof(pmc);
    if (GetProcessMemoryInfo(GetCurrentProcess(), (PROCESS_MEMORY_COUNTERS*)&pmc, sizeof(pmc))) {
        double mb = (double)pmc.WorkingSetSize / (1024.0 * 1024.0);
        wchar_t buf[64];
        swprintf_s(buf, L"ОЗУ: %.1f МБ / 256 МБ", mb);
        SetWindowTextW(g_hLblRam, buf);
    }
}

// Background thread for global hotkeys
DWORD WINAPI HotkeyThread(LPVOID lpParam) {
    RegisterHotKey(NULL, 1, MOD_CONTROL | MOD_ALT, 'S');
    RegisterHotKey(NULL, 2, MOD_CONTROL | MOD_ALT, 'W');

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        if (msg.message == WM_HOTKEY) {
            if (msg.wParam == 1) {
                PostMessageW(g_hWnd, WM_COMMAND, MAKEWPARAM(IDC_BTN_COPY, 0), (LPARAM)1);
            } else if (msg.wParam == 2) {
                PostMessageW(g_hWnd, WM_APP + 1, 0, 0);
            }
        }
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    UnregisterHotKey(NULL, 1);
    UnregisterHotKey(NULL, 2);
    return 0;
}

// Subclass for button hover tracking
LRESULT CALLBACK ModernBtnSubclass(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam, UINT_PTR uIdSubclass, DWORD_PTR dwRefData) {
    switch (msg) {
        case WM_MOUSEMOVE: {
            TRACKMOUSEEVENT tme = { sizeof(tme), TME_LEAVE, hWnd, 0 };
            TrackMouseEvent(&tme);
            if (!GetPropW(hWnd, L"HOVER")) {
                SetPropW(hWnd, L"HOVER", (HANDLE)1);
                InvalidateRect(hWnd, NULL, FALSE);
            }
            break;
        }
        case WM_MOUSELEAVE: {
            RemovePropW(hWnd, L"HOVER");
            InvalidateRect(hWnd, NULL, FALSE);
            break;
        }
        case WM_NCDESTROY: {
            RemovePropW(hWnd, L"HOVER");
            RemoveWindowSubclass(hWnd, ModernBtnSubclass, uIdSubclass);
            break;
        }
    }
    return DefSubclassProc(hWnd, msg, wParam, lParam);
}

// Custom modern dark rendering for all buttons
void DrawModernButton(LPDRAWITEMSTRUCT dis) {
    HDC hdc = dis->hDC;
    RECT rc = dis->rcItem;
    bool isHover = (GetPropW(dis->hwndItem, L"HOVER") != NULL);
    bool isPressed = (dis->itemState & ODS_SELECTED);
    int btnId = dis->CtlID;

    COLORREF bgCol = COLOR_CARD;
    COLORREF borderCol = COLOR_BORDER;
    COLORREF textCol = COLOR_TEXT;
    HFONT hFont = g_hFontUI;

    wchar_t textBuf[256] = { 0 };
    GetWindowTextW(dis->hwndItem, textBuf, 255);

    if (btnId == IDC_BTN_COPY) {
        if (wcsstr(textBuf, L"✓") != NULL) {
            bgCol = COLOR_GREEN;
            borderCol = COLOR_GREEN;
        } else {
            bgCol = isPressed ? RGB(30, 58, 138) : (isHover ? COLOR_ACCENT_HOVER : COLOR_ACCENT);
            borderCol = bgCol;
        }
        textCol = RGB(255, 255, 255);
        hFont = g_hFontBold;
    } else if (btnId == IDC_BTN_STYLE_SC) {
        if (!g_isWideMode) {
            bgCol = COLOR_ACCENT;
            borderCol = COLOR_ACCENT;
            textCol = RGB(255, 255, 255);
            hFont = g_hFontBold;
        } else {
            bgCol = isHover ? COLOR_CARD_HOVER : COLOR_CARD;
            borderCol = isHover ? RGB(100, 100, 110) : COLOR_BORDER;
            textCol = isHover ? COLOR_TEXT : COLOR_TEXT_DIM;
            hFont = g_hFontUI;
        }
    } else if (btnId == IDC_BTN_STYLE_WD) {
        if (g_isWideMode) {
            bgCol = COLOR_ACCENT;
            borderCol = COLOR_ACCENT;
            textCol = RGB(255, 255, 255);
            hFont = g_hFontBold;
        } else {
            bgCol = isHover ? COLOR_CARD_HOVER : COLOR_CARD;
            borderCol = isHover ? RGB(100, 100, 110) : COLOR_BORDER;
            textCol = isHover ? COLOR_TEXT : COLOR_TEXT_DIM;
            hFont = g_hFontUI;
        }
    } else if (btnId == IDC_BTN_TOPMOST) {
        if (g_isTopmost) {
            bgCol = COLOR_GREEN_DARK;
            borderCol = COLOR_GREEN;
            textCol = COLOR_GREEN;
        } else {
            bgCol = isHover ? COLOR_CARD_HOVER : COLOR_CARD;
            borderCol = isHover ? RGB(100, 100, 110) : COLOR_BORDER;
            textCol = isHover ? COLOR_TEXT : COLOR_TEXT_DIM;
        }
        hFont = g_hFontSmall;
    } else if (btnId == IDC_BTN_CLEAR) {
        bgCol = isHover ? COLOR_CARD_HOVER : COLOR_CARD;
        borderCol = isHover ? RGB(100, 100, 110) : COLOR_BORDER;
        textCol = isHover ? RGB(248, 113, 113) : COLOR_TEXT_DIM;
        hFont = g_hFontUI;
    } else if (btnId >= IDC_HIST_BTN_BASE && btnId < IDC_HIST_BTN_BASE + 8) {
        bgCol = isHover ? COLOR_CARD_HOVER : COLOR_CARD;
        borderCol = isHover ? RGB(100, 100, 110) : COLOR_BORDER;
        textCol = isHover ? COLOR_TEXT : COLOR_TEXT_DIM;
        hFont = g_hFontSmall;
    }

    int width = rc.right - rc.left;
    int height = rc.bottom - rc.top;

    HDC memDC = CreateCompatibleDC(hdc);
    HBITMAP hBmp = CreateCompatibleBitmap(hdc, width, height);
    HBITMAP hOldBmp = (HBITMAP)SelectObject(memDC, hBmp);

    // Parent background fill behind rounded rect
    HBRUSH hParentBr = CreateSolidBrush(COLOR_BG);
    RECT fullRc = { 0, 0, width, height };
    FillRect(memDC, &fullRc, hParentBr);
    DeleteObject(hParentBr);

    HBRUSH hBr = CreateSolidBrush(bgCol);
    HPEN hPen = CreatePen(PS_SOLID, 1, borderCol);
    HBRUSH hOldBr = (HBRUSH)SelectObject(memDC, hBr);
    HPEN hOldPen = (HPEN)SelectObject(memDC, hPen);

    RoundRect(memDC, 0, 0, width, height, 8, 8);

    SelectObject(memDC, hOldBr);
    SelectObject(memDC, hOldPen);
    DeleteObject(hBr);
    DeleteObject(hPen);

    SetBkMode(memDC, TRANSPARENT);
    SetTextColor(memDC, textCol);
    HFONT hOldFont = (HFONT)SelectObject(memDC, hFont);

    if (btnId >= IDC_HIST_BTN_BASE && btnId < IDC_HIST_BTN_BASE + 8) {
        RECT textRc = fullRc;
        textRc.left += 12;
        textRc.right -= 12;
        DrawTextW(memDC, textBuf, -1, &textRc, DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX);
    } else {
        DrawTextW(memDC, textBuf, -1, &fullRc, DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
    }

    SelectObject(memDC, hOldFont);

    BitBlt(hdc, rc.left, rc.top, width, height, memDC, 0, 0, SRCCOPY);

    SelectObject(memDC, hOldBmp);
    DeleteObject(hBmp);
    DeleteDC(memDC);
}

LRESULT CALLBACK WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_CREATE: {
            g_hWnd = hWnd;

            // Apply modern dark mode titlebar in Windows 10/11
            BOOL darkMode = TRUE;
            DwmSetWindowAttribute(hWnd, 20 /* DWMWA_USE_IMMERSIVE_DARK_MODE */, &darkMode, sizeof(darkMode));

            g_brBg = CreateSolidBrush(COLOR_BG);
            g_brCard = CreateSolidBrush(COLOR_CARD);
            g_brInput = CreateSolidBrush(COLOR_INPUT_BG);

            g_hFontUI = CreateFontW(-13, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
            g_hFontBold = CreateFontW(-14, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
            g_hFontSmall = CreateFontW(-11, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");

            // Header labels & buttons
            HWND hTitle = CreateWindowExW(0, L"STATIC", L"SmallCaps & Wide C++", WS_CHILD | WS_VISIBLE, 14, 12, 160, 24, hWnd, NULL, NULL, NULL);
            SendMessageW(hTitle, WM_SETFONT, (WPARAM)g_hFontBold, TRUE);

            g_hBtnTopmost = CreateWindowExW(0, L"BUTTON", L"📌 Закрепить", WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 180, 10, 100, 24, hWnd, (HMENU)IDC_BTN_TOPMOST, NULL, NULL);
            SetWindowSubclass(g_hBtnTopmost, ModernBtnSubclass, 0, 0);

            g_hLblBadge = CreateWindowExW(0, L"STATIC", L"⚡ Готов к вводу", WS_CHILD | WS_VISIBLE | SS_RIGHT, 285, 14, 245, 20, hWnd, (HMENU)IDC_BADGE_LABEL, NULL, NULL);
            SendMessageW(g_hLblBadge, WM_SETFONT, (WPARAM)g_hFontBold, TRUE);

            // Style buttons
            g_hBtnStyleSC = CreateWindowExW(0, L"BUTTON", L"ᴀʙᴄ Small Caps", WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 14, 40, 130, 26, hWnd, (HMENU)IDC_BTN_STYLE_SC, NULL, NULL);
            SetWindowSubclass(g_hBtnStyleSC, ModernBtnSubclass, 0, 0);

            g_hBtnStyleWD = CreateWindowExW(0, L"BUTTON", L"ＡＢＣ Широкий Моно", WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 150, 40, 150, 26, hWnd, (HMENU)IDC_BTN_STYLE_WD, NULL, NULL);
            SetWindowSubclass(g_hBtnStyleWD, ModernBtnSubclass, 0, 0);

            HWND hTip = CreateWindowExW(0, L"STATIC", L"Ctrl+Alt+S (буфер) | Ctrl+Alt+W (окно)", WS_CHILD | WS_VISIBLE | SS_RIGHT, 305, 45, 225, 18, hWnd, NULL, NULL, NULL);
            SendMessageW(hTip, WM_SETFONT, (WPARAM)g_hFontSmall, TRUE);

            // Input Text area (smooth dark border, no 3D client edge)
            HWND hInLbl = CreateWindowExW(0, L"STATIC", L"Исходный текст (RU / EN):", WS_CHILD | WS_VISIBLE, 14, 72, 250, 18, hWnd, NULL, NULL, NULL);
            SendMessageW(hInLbl, WM_SETFONT, (WPARAM)g_hFontSmall, TRUE);

            g_hEditIn = CreateWindowExW(0, L"EDIT", L"", WS_CHILD | WS_VISIBLE | WS_VSCROLL | ES_MULTILINE | ES_AUTOVSCROLL | ES_WANTRETURN, 14, 92, 520, 80, hWnd, (HMENU)IDC_INPUT_TEXT, NULL, NULL);
            SendMessageW(g_hEditIn, WM_SETFONT, (WPARAM)g_hFontUI, TRUE);
            SendMessageW(g_hEditIn, EM_SETMARGINS, EC_LEFTMARGIN | EC_RIGHTMARGIN, MAKELPARAM(8, 8));

            // Output Text area (smooth dark border, no 3D client edge)
            HWND hOutLbl = CreateWindowExW(0, L"STATIC", L"Результат:", WS_CHILD | WS_VISIBLE, 14, 178, 250, 18, hWnd, NULL, NULL, NULL);
            SendMessageW(hOutLbl, WM_SETFONT, (WPARAM)g_hFontSmall, TRUE);

            g_hEditOut = CreateWindowExW(0, L"EDIT", L"", WS_CHILD | WS_VISIBLE | WS_VSCROLL | ES_MULTILINE | ES_AUTOVSCROLL | ES_READONLY, 14, 198, 520, 80, hWnd, (HMENU)IDC_OUTPUT_TEXT, NULL, NULL);
            SendMessageW(g_hEditOut, WM_SETFONT, (WPARAM)g_hFontUI, TRUE);
            SendMessageW(g_hEditOut, EM_SETMARGINS, EC_LEFTMARGIN | EC_RIGHTMARGIN, MAKELPARAM(8, 8));

            // Action Buttons
            g_hBtnCopy = CreateWindowExW(0, L"BUTTON", L"📋 Скопировать одной кнопкой", WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 14, 286, 380, 32, hWnd, (HMENU)IDC_BTN_COPY, NULL, NULL);
            SetWindowSubclass(g_hBtnCopy, ModernBtnSubclass, 0, 0);

            g_hBtnClear = CreateWindowExW(0, L"BUTTON", L"✕ Очистить", WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, 404, 286, 130, 32, hWnd, (HMENU)IDC_BTN_CLEAR, NULL, NULL);
            SetWindowSubclass(g_hBtnClear, ModernBtnSubclass, 0, 0);

            // History Section
            HWND hHistLbl = CreateWindowExW(0, L"STATIC", L"История последних записей (клик для копирования):", WS_CHILD | WS_VISIBLE, 14, 326, 400, 18, hWnd, NULL, NULL, NULL);
            SendMessageW(hHistLbl, WM_SETFONT, (WPARAM)g_hFontSmall, TRUE);

            int histY = 346;
            for (int i = 0; i < 6; i++) {
                HWND hBtn = CreateWindowExW(0, L"BUTTON", L"", WS_CHILD | BS_OWNERDRAW, 14, histY, 520, 24, hWnd, (HMENU)(INT_PTR)(IDC_HIST_BTN_BASE + i), NULL, NULL);
                SetWindowSubclass(hBtn, ModernBtnSubclass, 0, 0);
                g_histButtons.push_back(hBtn);
                histY += 26;
            }

            // Status bar
            g_hLblStatus = CreateWindowExW(0, L"STATIC", L"Лимиты: CPU <= 20% + ОЗУ <= 256МБ", WS_CHILD | WS_VISIBLE, 14, 510, 300, 20, hWnd, (HMENU)IDC_STATUS_LABEL, NULL, NULL);
            SendMessageW(g_hLblStatus, WM_SETFONT, (WPARAM)g_hFontSmall, TRUE);

            g_hLblRam = CreateWindowExW(0, L"STATIC", L"ОЗУ: ~1.2 МБ / 256 МБ", WS_CHILD | WS_VISIBLE | SS_RIGHT, 320, 510, 214, 20, hWnd, (HMENU)IDC_RAM_LABEL, NULL, NULL);
            SendMessageW(g_hLblRam, WM_SETFONT, (WPARAM)g_hFontSmall, TRUE);

            // Setup System Tray
            g_nid.cbSize = sizeof(NOTIFYICONDATAW);
            g_nid.hWnd = hWnd;
            g_nid.uID = 101;
            g_nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP;
            g_nid.uCallbackMessage = WM_TRAYICON;
            g_nid.hIcon = (HICON)LoadImageW(GetModuleHandleW(NULL), MAKEINTRESOURCEW(1), IMAGE_ICON, 16, 16, LR_SHARED);
            if (!g_nid.hIcon) g_nid.hIcon = LoadIconW(NULL, IDI_APPLICATION);
            wcscpy_s(g_nid.szTip, L"SmallCaps C++");
            Shell_NotifyIconW(NIM_ADD, &g_nid);

            // Timers
            SetTimer(hWnd, 2, 2000, NULL); // RAM counter update

            // Global Hotkeys background thread
            CreateThread(NULL, 0, HotkeyThread, NULL, 0, NULL);
            break;
        }

        case WM_TIMER: {
            if (wParam == 1) { // Reset copy button text
                KillTimer(hWnd, 1);
                SetWindowTextW(g_hBtnCopy, L"📋 Скопировать одной кнопкой");
                InvalidateRect(g_hBtnCopy, NULL, FALSE);
            } else if (wParam == 2) {
                UpdateRamCounter();
            }
            break;
        }

        case WM_DRAWITEM: {
            LPDRAWITEMSTRUCT dis = (LPDRAWITEMSTRUCT)lParam;
            if (dis->CtlType == ODT_BUTTON) {
                DrawModernButton(dis);
                return TRUE;
            }
            break;
        }

        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC hdc = BeginPaint(hWnd, &ps);

            // Draw crisp dark borders around the edit controls
            HPEN hBorderPen = CreatePen(PS_SOLID, 1, COLOR_BORDER);
            HBRUSH hOldBr = (HBRUSH)SelectObject(hdc, GetStockObject(NULL_BRUSH));
            HPEN hOldPen = (HPEN)SelectObject(hdc, hBorderPen);

            // Border around Input Text (14, 92, w=520, h=80)
            RoundRect(hdc, 13, 91, 535, 173, 6, 6);

            // Border around Output Text (14, 198, w=520, h=80)
            RoundRect(hdc, 13, 197, 535, 279, 6, 6);

            SelectObject(hdc, hOldBr);
            SelectObject(hdc, hOldPen);
            DeleteObject(hBorderPen);

            EndPaint(hWnd, &ps);
            break;
        }

        case WM_APP + 1: { // Toggle window hotkey
            ToggleAppWindow();
            break;
        }

        case WM_TRAYICON: {
            if (lParam == WM_LBUTTONUP || lParam == WM_LBUTTONDBLCLK) {
                ToggleAppWindow();
            } else if (lParam == WM_RBUTTONUP) {
                POINT pt;
                GetCursorPos(&pt);
                HMENU hMenu = CreatePopupMenu();
                InsertMenuW(hMenu, 0, MF_BYPOSITION | MF_STRING, IDM_TRAY_RESTORE, L"Развернуть");
                InsertMenuW(hMenu, 1, MF_BYPOSITION | MF_SEPARATOR, 0, NULL);
                InsertMenuW(hMenu, 2, MF_BYPOSITION | MF_STRING, IDM_TRAY_EXIT, L"Выход");
                SetForegroundWindow(hWnd);
                TrackPopupMenu(hMenu, TPM_RIGHTBUTTON, pt.x, pt.y, 0, hWnd, NULL);
                DestroyMenu(hMenu);
            }
            break;
        }

        case WM_COMMAND: {
            int id = LOWORD(wParam);
            int code = HIWORD(wParam);

            if (id == IDC_INPUT_TEXT && code == EN_CHANGE) {
                UpdateConversion();
            } else if (id == IDC_BTN_COPY) {
                if (lParam == 1) {
                    OnGlobalHotkeyConvert();
                } else {
                    int len = GetWindowTextLengthW(g_hEditOut);
                    std::wstring outText(len, L'\0');
                    GetWindowTextW(g_hEditOut, &outText[0], len + 1);
                    CopyToClipboard(outText);
                }
            } else if (id == IDC_BTN_CLEAR) {
                SetWindowTextW(g_hEditIn, L"");
                SetWindowTextW(g_hEditOut, L"");
                SetFocus(g_hEditIn);
            } else if (id == IDC_BTN_TOPMOST) {
                g_isTopmost = !g_isTopmost;
                SetWindowPos(hWnd, g_isTopmost ? HWND_TOPMOST : HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE);
                SetWindowTextW(g_hBtnTopmost, g_isTopmost ? L"📌 Закреплено" : L"📌 Закрепить");
                InvalidateRect(g_hBtnTopmost, NULL, FALSE);
            } else if (id == IDC_BTN_STYLE_SC) {
                g_isWideMode = false;
                InvalidateRect(g_hBtnStyleSC, NULL, FALSE);
                InvalidateRect(g_hBtnStyleWD, NULL, FALSE);
                UpdateConversion();
            } else if (id == IDC_BTN_STYLE_WD) {
                g_isWideMode = true;
                InvalidateRect(g_hBtnStyleSC, NULL, FALSE);
                InvalidateRect(g_hBtnStyleWD, NULL, FALSE);
                UpdateConversion();
            } else if (id >= IDC_HIST_BTN_BASE && id < IDC_HIST_BTN_BASE + 8) {
                size_t idx = id - IDC_HIST_BTN_BASE;
                if (idx < g_history.size()) {
                    SetWindowTextW(g_hEditOut, g_history[idx].c_str());
                    CopyToClipboard(g_history[idx]);
                }
            } else if (id == IDM_TRAY_RESTORE) {
                ShowAppWindow();
            } else if (id == IDM_TRAY_EXIT) {
                DestroyWindow(hWnd);
            }
            break;
        }

        case WM_CTLCOLORSTATIC: {
            HDC hdc = (HDC)wParam;
            HWND hCtrl = (HWND)lParam;
            if (hCtrl == g_hEditOut) {
                SetBkColor(hdc, COLOR_INPUT_BG);
                SetTextColor(hdc, COLOR_TEXT);
                return (LRESULT)g_brInput;
            }
            SetBkColor(hdc, COLOR_BG);
            if (hCtrl == g_hLblBadge) {
                SetTextColor(hdc, COLOR_GREEN);
            } else if (hCtrl == g_hLblRam || hCtrl == g_hLblStatus) {
                SetTextColor(hdc, COLOR_TEXT_DIM);
            } else {
                SetTextColor(hdc, COLOR_TEXT);
            }
            return (LRESULT)g_brBg;
        }

        case WM_CTLCOLOREDIT: {
            HDC hdc = (HDC)wParam;
            SetBkColor(hdc, COLOR_INPUT_BG);
            SetTextColor(hdc, COLOR_TEXT);
            return (LRESULT)g_brInput;
        }

        case WM_CLOSE: {
            HideAppWindow();
            return 0; // Don't destroy window on [X], minimize to tray and free RAM!
        }

        case WM_DESTROY: {
            Shell_NotifyIconW(NIM_DELETE, &g_nid);
            if (g_brBg) DeleteObject(g_brBg);
            if (g_brCard) DeleteObject(g_brCard);
            if (g_brInput) DeleteObject(g_brInput);
            if (g_hFontUI) DeleteObject(g_hFontUI);
            if (g_hFontBold) DeleteObject(g_hFontBold);
            if (g_hFontSmall) DeleteObject(g_hFontSmall);
            PostQuitMessage(0);
            break;
        }

        default:
            return DefWindowProcW(hWnd, msg, wParam, lParam);
    }
    return 0;
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    ApplyResourceLimits();

    WNDCLASSEXW wc = { 0 };
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hCursor = LoadCursorW(NULL, IDC_ARROW);
    wc.hbrBackground = CreateSolidBrush(COLOR_BG);
    wc.lpszClassName = L"SmallCapsCppClass";
    wc.hIcon = (HICON)LoadImageW(hInstance, MAKEINTRESOURCEW(1), IMAGE_ICON, 32, 32, LR_SHARED);
    wc.hIconSm = (HICON)LoadImageW(hInstance, MAKEINTRESOURCEW(1), IMAGE_ICON, 16, 16, LR_SHARED);
    RegisterClassExW(&wc);

    HWND hWnd = CreateWindowExW(
        0, wc.lpszClassName, L"SmallCaps & Wide C++",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        CW_USEDEFAULT, CW_USEDEFAULT, 564, 576,
        NULL, NULL, hInstance, NULL
    );

    if (!hWnd) return 0;

    ShowWindow(hWnd, nCmdShow);
    UpdateWindow(hWnd);

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    return (int)msg.wParam;
}
