"""Клодик — маленькая пиксельная версия Claude, живёт внизу экрана и умеет управлять компом.
ЛКМ — поговорить/попросить, перетаскивание — поднять и бросить, поводить мышкой по нему — погладить, ПКМ — меню.
Тест: python pet.pyw --selftest"""
import ctypes, difflib, importlib.machinery, importlib.util, json, math, os, queue, random, re, shutil, struct
import subprocess, sys, threading, time, tkinter as tk, traceback, urllib.parse, urllib.request, winreg, winsound
from ctypes import wintypes as wt
from tkinter import messagebox

FROZEN = getattr(sys, "frozen", False)               # собран в Klodik.exe
HERE = sys.executable and os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.environ.get("APPDATA", HERE), "Klodik")
STATE = os.path.join(DATA_DIR, "state.json")
INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", HERE), "Programs", "Klodik")
OLLAMA = "http://127.0.0.1:11434"
OLLAMA_MODELS = ("qwen2.5:7b", "qwen2.5:3b")          # qwen2.5 нормально говорит по-русски; 7b умнее, 3b для слабых ПК
BRAINS = {"ollama": "ИИ на компе (Ollama, бесплатно)", "none": "Без ИИ (только команды)",
          "claude": "Claude (тратит токены подписки)"}
VOSK_MODEL = "vosk-model-small-ru-0.22"            # офлайн-распознавание русской речи, ~45 МБ
VOSK_URL = f"https://alphacephei.com/vosk/models/{VOSK_MODEL}.zip"
# «Клодик» нет в словаре модели — она слышит его как «клади к», «клод…», «колод…»
WAKE = re.compile(r"^(?:эй |слушай |ну )?(?:клод\w*|клади(?:\s+к\b)?|колод\w*|кладик\w*|глади\s+к\b|плоди\s+к\b)\s*")
CANNED = ["Я пока без мозгов для болтовни, но команды знаю! Скажи «открой Steam» или «разгреби».",
          "Хе-хе. Лучше дай задание: «засеки 5 минут», «позови друга», «сфоткай».",
          "Болтать не умею, зато умею бульдозер. Скажи «разгреби»!",
          "Чтобы я болтал, поставь Ollama (ПКМ → Мозг). А пока — «залезь на окно»?"]
LAUNCHER = r"C:\Users\PC\MiniLauncher\launcher.pyw"
KEY = "#ff00fe"                      # цвет-прозрачность (клики сквозь него проходят)
C = 5                                # размер «пикселя»
W, H = 110, 90                       # окно; спрайт 16×10 клеток стоит внизу по центру
OX = (W - 16 * C) // 2
ORANGE, EYE, INK, PAPER, DARK = "#d97757", "#1b1b1b", "#2b1d18", "#fff7f0", "#a9503a"
BUDDY = "#8b7cff"
TICK_MS = 7                          # ~144 кадра в секунду
G = 750.0                            # гравитация, px/с²
WALK, RUN, CHASE = 50.0, 170.0, 115.0
NOWIN = 0x08000000                   # CREATE_NO_WINDOW
u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
PHRASES = ["Я просто гуляю", "Попей воды, а?", "Сделай перерыв", "Я слежу за компом", "Хорошо сидим",
           "Кликни — поболтаем", "Скажи «открой Steam» — сбегаю", "Погладь меня мышкой",
           "Скажи «разгреби» — приеду на бульдозере", "Могу запрыгнуть на окно"]
JUNK = re.compile(r"help|uninstall|удал|readme|справк|documentation|manual|website|tutorial|release notes|licen",
                  re.I)
SAFE_PROCS = {"claude.exe", "diabloimmortal.exe"}     # бульдозер их не трогает
HATS = {"auto": "Авто (ночью колпак, зимой шапка)", "none": "Без шапки", "helmet": "Каска", "crown": "Корона",
        "glasses": "Крутые очки", "nightcap": "Ночной колпак", "winter": "Зимняя шапка"}
HAT_WORDS = {"каск": "helmet", "корон": "crown", "очк": "glasses", "колпак": "nightcap", "шапк": "winter"}
LANDABLE = ("walk", "idle", "climb", "sleep")        # в этих состояниях можно приземлиться на окно
# Команды разбираются локально (0 токенов); в ИИ (Ollama на компе) уходит только болтовня — с коротким промптом.
SYSTEM = ("Ты Клодик — маленький пиксельный помощник, живёшь на рабочем столе пользователя. "
          "Пиши ТОЛЬКО по-русски, без английских слов. 1–2 коротких предложения, по-дружески, без markdown. "
          "Команды вида «открой/закрой/сверни X», «громче/тише», «пауза», «найди X», «разгреби все окна», "
          "«засеки 5 минут», «сфоткай», «позови друга», «залезь на окно», «надень каску» ты выполняешь сам — "
          "Если не знаешь ответа — честно скажи, не выдумывай. "
          "ВАЖНО: фразы приходят с распознавания голоса и бывают расслышаны неправильно. Если сообщение похоже на "
          "искажённую команду из списка выше (например «открой стимм», «разгромив все окна», «засеки пяти минут») — "
          "ответь ТОЛЬКО одной строкой «CMD: <правильная команда>», без других слов. Иначе отвечай как обычно.")
OPEN_V = r"открой|открыть|запусти|запустить|включи|вруби|зайди в|зайди на"
WIN_V = {"close": r"закрой|закрыть|выруби|выключи", "minimize": r"сверни|свернуть|спрячь",
         "maximize": r"разверни|развернуть", "focus": r"покажи|переключись на|переключи на|перейди в"}
ALIAS = {"стим": "steam", "хром": "chrome", "гугл хром": "chrome", "клод": "claude", "клауд": "claude",
         "телега": "telegram", "телеграм": "telegram", "тг": "telegram", "дс": "discord", "дискорд": "discord",
         "капкат": "capcut", "кап кат": "capcut", "файрфокс": "firefox", "фаерфокс": "firefox", "обс": "obs",
         "ютуб": "youtube", "гугл": "google", "вк": "vk", "гитхаб": "github", "почту": "gmail", "почта": "gmail",
         "блендер": "blender", "роблокс": "roblox", "фигма": "figma", "диабло": "diablo"}
URLS = {"youtube": "https://youtube.com", "google": "https://google.com", "vk": "https://vk.com",
        "github": "https://github.com", "gmail": "https://mail.google.com"}
DIRECT = {"проводник": "explorer.exe", "диспетчер задач": "taskmgr.exe", "блокнот": "notepad.exe",
          "калькулятор": "calc.exe", "настройки": "ms-settings:", "параметры": "ms-settings:"}
TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
              "a b v g d e e zh z i i k l m n o p r s t u f h c ch sh sch _ y _ e yu ya".split()))
NUMWORD = {"одну": 1, "один": 1, "две": 2, "два": 2, "три": 3, "пять": 5, "десять": 10, "пятнадцать": 15}
SHOT_PS = ("Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
           "$b=[System.Windows.Forms.SystemInformation]::VirtualScreen;"
           "$m=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
           "$g=[System.Drawing.Graphics]::FromImage($m);$g.CopyFromScreen($b.Left,$b.Top,0,0,$m.Size);"
           "$m.Save($env:PET_SHOT,[System.Drawing.Imaging.ImageFormat]::Png)")


def tr(s):
    return "".join(TR.get(ch, ch) for ch in s.lower()).replace("_", "")


def match(q, name):
    """Насколько запрос q похож на имя (0..1), с учётом кириллицы/латиницы."""
    q, n = tr(q), tr(name)
    if not q or not n:
        return 0.0
    if q == n:
        return 1.0
    if len(q) >= 3 and q in n:
        return 0.9
    return difflib.SequenceMatcher(None, q, n).ratio()


NUM_ONES = {"ноль": 0, "один": 1, "одну": 1, "одна": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5,
            "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10, "одиннадцать": 11, "двенадцать": 12,
            "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17,
            "восемнадцать": 18, "девятнадцать": 19}
NUM_TENS = {"двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70,
            "восемьдесят": 80, "девяносто": 90, "сто": 100}


def num_words(text):
    """Распознавалка пишет числа словами: «двадцать пять минут» → «25 минут»."""
    out, acc = [], None
    for w in text.split():
        if w in NUM_TENS:
            if acc is not None:
                out.append(str(acc))
            acc = NUM_TENS[w]
        elif w in NUM_ONES:
            if acc is not None and acc % 10 == 0 and acc >= 20 and NUM_ONES[w] < 10:
                acc += NUM_ONES[w]
            else:
                if acc is not None:
                    out.append(str(acc))
                acc = NUM_ONES[w]
        else:
            if acc is not None:
                out.append(str(acc))
                acc = None
            out.append(w)
    if acc is not None:
        out.append(str(acc))
    return " ".join(out)


def parse_duration(seg):
    """«через 10 минут», «полчаса», «1 час 20 мин» → секунды (0 — времени нет)."""
    seg = num_words(seg)
    seg = seg.replace("полчаса", "30 мин").replace("полтора часа", "90 мин").replace("полминуты", "30 сек")
    total = 0
    for num, unit in re.findall(r"(?:(\d+|" + "|".join(NUMWORD) + r")\s+)?\b(сек|мин|час)", seg):
        n = int(num) if num.isdigit() else NUMWORD.get(num, 1)
        total += n * {"сек": 1, "мин": 60, "час": 3600}[unit]
    return total


def reminder_text(seg):
    t = re.sub(r"\b(?:засеки|поставь|таймер|будильник|напомни(?:\s+мне)?|через)\b", " ", seg)
    t = re.sub(r"\bна\s+(?=\d)", " ", t)
    t = re.sub(r"(?:\b(?:\d+|" + "|".join(NUMWORD) + r")\s+)?\b(?:сек|мин|час)\w*", " ", t)
    return re.sub(r"\s+", " ", t).strip(" ,.-")


def fmt_secs(sec):
    sec = int(sec)
    if sec < 60:
        return f"{sec} сек"
    h, m = divmod(sec // 60, 60)
    return f"{h} ч {m} мин" if h else f"{m} мин"


def is_night():
    return time.localtime().tm_hour >= 23 or time.localtime().tm_hour < 6


def work_area():
    # shortcut: только основной монитор; для нескольких мониторов брать MonitorFromWindow
    r = wt.RECT()
    u32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)
    return r.left, r.top, r.right, r.bottom


def pictures_dir():
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(0, 0x27, 0, 0, buf)      # CSIDL_MYPICTURES (учитывает OneDrive)
    return os.path.join(buf.value or os.path.expanduser("~"), "Клодик")


def run_quiet(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, creationflags=NOWIN, **kw)
    except (OSError, subprocess.SubprocessError) as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def start_button_x(L, R):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced") as k:
            left = winreg.QueryValueEx(k, "TaskbarAl")[0] == 0
    except OSError:
        left = False
    return L + 40 if left else (L + R) / 2 - 110   # shortcut: «Пуск» по центру — примерно, без учёта числа значков



def special_dir(csidl):
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(0, csidl, 0, 0, buf)
    return buf.value
