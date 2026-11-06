import ctypes
from ctypes import wintypes
from datetime import datetime
import math
import tkinter as tk

# --- DIMENSIONS & COLORS ---
MIN_WIDTH = 100
MIN_HEIGHT = 6      # tiny 6px sliver at y=0 so it never blocks browser tabs
MAX_WIDTH = 380
MAX_HEIGHT = 118

BG_COLOR = "#0a0a0a"
ACCENT_GREEN = "#a3a5a4"
DARK_GREEN = "#143322"
MUTED_TEXT = "#8a8a8a"
TRANSPARENT_COLOR = "#ff00ff"

# --- ANIMATION STATE ---
current_w = float(MIN_WIDTH)
current_h = float(MIN_HEIGHT)
target_w = float(MIN_WIDTH)
target_h = float(MIN_HEIGHT)
is_expanded = False
animating = False

# --- WINDOWS NATIVE BATTERY HOOK (NO PIP INSTALL NEEDED) ---


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("SystemStatusFlag", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def get_battery_info():
    status = SYSTEM_POWER_STATUS()
    ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
    pct = status.BatteryLifePercent
    if pct > 100:
        pct = 100
    charging = (status.ACLineStatus == 1)
    return pct, charging


# --- WINDOWS NATIVE MEDIA KEYS & SONG DETECTOR ---
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3


def send_media_key(vk_code):
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)


def get_current_media():
    titles = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def foreach_window(hwnd, _lparam):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                titles.append(buff.value)
        return True

    ctypes.windll.user32.EnumWindows(EnumWindowsProc(foreach_window), 0)

    # scan open windows for Apple Music, Spotify, or YouTube Music
    for t in titles:
        if "Apple Music" in t:
            clean = t.split(" - Apple Music")[0].split(" — Apple Music")[0]
            return f"♫ {clean[:30]}"
        if " - YouTube Music" in t:
            clean = t.split(" - YouTube Music")[0]
            return f"♫ {clean[:30]}"
        # Spotify desktop app shows "Artist - Song" when playing
        if " - " in t and not any(b in t for b in ("Chrome", "Edge", "Firefox", "Visual Studio", "Brave", "Discord")):
            if len(t) < 65:
                return f"♫ {t[:30]}"

    return "♫ Media Ready"

# --- GEOMETRY MATH ---


def rounded_rectangle_points(x1, y1, x2, y2, radius, steps=12):
    points = []
    radius = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    corners = (
        (x2 - radius, y1 + radius, -90, 0),
        (x2 - radius, y2 - radius, 0, 90),
        (x1 + radius, y2 - radius, 90, 180),
        (x1 + radius, y1 + radius, 180, 270),
    )
    for center_x, center_y, start_angle, end_angle in corners:
        for step in range(steps + 1):
            angle = math.radians(
                start_angle + (end_angle - start_angle) * step / steps)
            points.extend((
                center_x + radius * math.cos(angle),
                center_y + radius * math.sin(angle),
            ))
    return points

# --- UI DRAWING ---


def draw_island():
    w = int(current_w)
    h = int(current_h)
    canvas.delete("all")

    # pin to the very top center (y=0 when collapsed, y=6 when open)
    x = (screen_width - w) // 2
    y = 0 if h < 20 else 6
    root.geometry(f"{w}x{h}+{x}+{y}")
    canvas.config(width=w, height=h)

    # draw outer black pill with green accent border when expanded
    border_col = ACCENT_GREEN if h > 30 else BG_COLOR
    canvas.create_polygon(
        rounded_rectangle_points(1, 1, w - 1, h - 1, radius=min(28, h // 2)),
        fill=BG_COLOR,
        outline=border_col,
        width=1,
    )

    # if collapsed, just draw a tiny neon green indicator line
    if h <= 20:
        bar_w = 36
        canvas.create_line(
            (w - bar_w) // 2, h // 2, (w + bar_w) // 2, h // 2,
            fill=ACCENT_GREEN, width=2, capstyle="round"
        )
        return

    # only draw the dashboard widgets once it's opened enough
    if h > 85:
        now = datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%a, %b %d").upper()
        batt_pct, charging = get_battery_info()
        song_title = get_current_media()

        # 1. Clock & Date (Top Left)
        canvas.create_text(
            22, 26, text=time_str, fill="white",
            font=("Segoe UI", 14, "bold"), anchor="w"
        )
        canvas.create_text(
            22, 46, text=date_str, fill=ACCENT_GREEN,
            font=("Segoe UI", 8, "bold"), anchor="w"
        )

        # 2. Battery Pill (Top Right)
        batt_x = w - 115
        batt_y = 26
        bolt = "⚡" if charging else ""
        canvas.create_text(
            batt_x, batt_y, text=f"{bolt}{batt_pct}%",
            fill=ACCENT_GREEN, font=("Segoe UI", 10, "bold"), anchor="e"
        )
        # mini battery bar background + fill
        canvas.create_rectangle(
            batt_x + 6, batt_y - 6, batt_x + 34, batt_y + 6, outline=ACCENT_GREEN, width=1)
        fill_w = max(2, int(24 * (batt_pct / 100)))
        canvas.create_rectangle(batt_x + 8, batt_y - 4, batt_x +
                                8 + fill_w, batt_y + 4, fill=ACCENT_GREEN, outline="")

        # 3. Close Button (Top Far Right)
        bx, by = w - 28, 26
        close_bg = canvas.create_oval(
            bx - 11, by - 11, bx + 11, by + 11, fill="#1f1f1f", outline=DARK_GREEN)
        close_txt = canvas.create_text(
            bx, by - 1, text="×", fill=ACCENT_GREEN, font=("Segoe UI", 13, "bold"))
        for item in (close_bg, close_txt):
            canvas.tag_bind(item, "<Button-1>", lambda _e: root.destroy())

        # 4. Divider Line
        canvas.create_line(22, 62, w - 22, 62, fill=DARK_GREEN, width=1)

        # 5. Media Player Row (Bottom)
        canvas.create_text(
            22, 88, text=song_title, fill="white",
            font=("Segoe UI", 10), anchor="w"
        )

        # Media Controls: Prev, Play/Pause, Next
        controls = [
            ("⏮", w - 105, VK_MEDIA_PREV_TRACK),
            ("⏯", w - 68, VK_MEDIA_PLAY_PAUSE),
            ("⏭", w - 31, VK_MEDIA_NEXT_TRACK),
        ]
        for symbol, cx, vk in controls:
            btn_bg = canvas.create_oval(
                cx - 14, 88 - 14, cx + 14, 88 + 14, fill=DARK_GREEN, outline=ACCENT_GREEN)
            btn_txt = canvas.create_text(
                cx, 88 - 1, text=symbol, fill=ACCENT_GREEN, font=("Segoe UI Symbol", 10))
            for item in (btn_bg, btn_txt):
                canvas.tag_bind(item, "<Button-1>", lambda _e,
                                code=vk: send_media_key(code))

# --- SMOOTH 2D ANIMATION ENGINE ---


def animate():
    global current_w, current_h, animating

    # smooth easing math (moves 25% of the remaining distance each frame)
    diff_w = target_w - current_w
    diff_h = target_h - current_h

    if abs(diff_w) > 1 or abs(diff_h) > 1:
        current_w += diff_w * 0.25
        current_h += diff_h * 0.25
        draw_island()
        root.after(12, animate)
    else:
        current_w = target_w
        current_h = target_h
        animating = False
        draw_island()


def start_animation():
    global animating
    if not animating:
        animating = True
        animate()


def on_enter(_event):
    global target_w, target_h, is_expanded
    is_expanded = True
    target_w = MAX_WIDTH
    target_h = MAX_HEIGHT
    start_animation()


def on_leave(_event):
    global target_w, target_h, is_expanded
    # check if mouse actually left the window area
    mx = root.winfo_pointerx() - root.winfo_rootx()
    my = root.winfo_pointery() - root.winfo_rooty()
    if 0 <= mx <= current_w and 0 <= my <= current_h:
        return
    is_expanded = False
    target_w = MIN_WIDTH
    target_h = MIN_HEIGHT
    start_animation()

# live refresh loop for clock, battery, and song title while open


def live_refresh():
    if is_expanded and not animating:
        draw_island()
    root.after(1000, live_refresh)


# --- WINDOW SETUP ---
root = tk.Tk()
root.overrideredirect(True)
root.wm_attributes("-topmost", True)
root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)

screen_width = root.winfo_screenwidth()
root.configure(bg=TRANSPARENT_COLOR)

canvas = tk.Canvas(
    root, width=MIN_WIDTH, height=MIN_HEIGHT,
    bg=TRANSPARENT_COLOR, highlightthickness=0, borderwidth=0, cursor="hand2"
)
canvas.pack()

canvas.bind("<Enter>", on_enter)
canvas.bind("<Leave>", on_leave)

draw_island()
live_refresh()
root.mainloop()
