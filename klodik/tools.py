"""«Руки» Клодика: реестр инструментов. У каждого — категория риска из policy.json, описание для ИИ-плана,
выполнение и (где можно) откат. Всё через штатные средства Windows; системные и защитные вещи не трогаем."""
import ctypes
import glob as _glob

from .common import *  # noqa: F401,F403

READONLY = re.compile(r"^\s*(?:Get-\w+|Test-\w+|Measure-\w+|Select-\w+|Resolve-DnsName|ipconfig(?:\s+/all)?|systeminfo|"
                      r"whoami|ping\s|tracert\s|nslookup\s|tasklist|driverquery|netstat\s+-an?o?|wmic\s+\w+\s+get)\b", re.I)
DANGER = re.compile(r"Remove-Item|rm\s|del\s|rd\s|rmdir|format|diskpart|bcdedit|reg\s+delete|Set-MpPreference|"
                    r"netsh\s+advfirewall|Stop-Service|sc\s+(?:stop|delete)|shutdown|Clear-|Disable-", re.I)


def ps(cmd, timeout=60):
    r = run_quiet(["powershell", "-NoProfile", "-Command", "[Console]::OutputEncoding=[Text.Encoding]::UTF8;" + cmd],
                  encoding="utf-8", errors="replace", timeout=timeout)
    return (r.stdout or "").strip(), (r.stderr or "").strip(), r.returncode


# --- громкость (pycaw: точный процент) ---
def _endpoint():
    import comtypes
    from ctypes import POINTER, cast
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    comtypes.CoInitialize()
    dev = AudioUtilities.GetSpeakers()
    return cast(getattr(dev, "_dev", dev).Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None), POINTER(IAudioEndpointVolume))


def get_volume():
    return round(_endpoint().GetMasterVolumeLevelScalar() * 100)


def set_volume(percent):
    _endpoint().SetMasterVolumeLevelScalar(max(0, min(100, float(percent))) / 100, None)


def get_brightness():
    out, err, _ = ps("(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction Stop).CurrentBrightness")
    if not out.strip().isdigit():
        raise RuntimeError("у этого монитора нет управления яркостью из Windows (обычно так у внешних мониторов)")
    return int(out.split()[0])


def set_brightness(percent):
    get_brightness()
    _, err, code = ps(f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods)"
                      f".WmiSetBrightness(1,{int(max(0, min(100, float(percent))))}) | Out-Null")
    if code:
        raise RuntimeError(err[:120] or "не удалось")


PLANS = {"balanced": "SCHEME_BALANCED", "high": "SCHEME_MIN", "saver": "SCHEME_MAX"}   # MIN = макс. производительность


def get_power_plan():
    out, _, _ = ps("powercfg /getactivescheme")
    m = re.search(r"([0-9a-f-]{36})", out)
    return m[1] if m else None


def set_power_plan(plan):
    target = PLANS.get(plan, plan)
    r = run_quiet(["powercfg", "/setactive", target], timeout=20)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout or "план не найден").strip()[:120])


THEME_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


def get_theme():
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, THEME_KEY) as k:
        return "light" if winreg.QueryValueEx(k, "AppsUseLightTheme")[0] else "dark"


def set_theme(mode):
    import winreg
    v = 1 if mode == "light" else 0
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, THEME_KEY, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "AppsUseLightTheme", 0, winreg.REG_DWORD, v)
        winreg.SetValueEx(k, "SystemUsesLightTheme", 0, winreg.REG_DWORD, v)


def winget_find(name):
    r = run_quiet(["winget", "search", "--accept-source-agreements", name], encoding="utf-8", errors="replace", timeout=60)
    for line in (r.stdout or "").splitlines():
        cols = re.split(r"\s{2,}", line.strip())
        if len(cols) >= 3 and "." in cols[1] and not line.startswith(("-", "Name", "Имя")):
            return cols[0], cols[1], cols[-1]              # имя, id, источник
    return None


def autostart():
    import winreg
    out = []
    for hive, path in ((winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                       (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")):
        try:
            with winreg.OpenKey(hive, path) as k:
                i = 0
                while True:
                    try:
                        out.append(winreg.EnumValue(k, i)[0])
                        i += 1
                    except OSError:
                        break
        except OSError:
            pass
    out += [os.path.splitext(os.path.basename(f))[0] for f in _glob.glob(os.path.join(special_dir(0x07), "*.lnk"))]
    return out


def temp_junk(days=2):
    """Временные файлы старше N дней: (путь, размер)."""
    lim, out = time.time() - days * 86400, []
    for root, _, files in os.walk(os.environ.get("TEMP", "")):
        for f in files:
            p = os.path.join(root, f)
            try:
                st = os.stat(p)
                if st.st_mtime < lim:
                    out.append((p, st.st_size))
            except OSError:
                pass
        if len(out) > 3000:
            break
    return out


def internet():
    r = run_quiet(["ping", "-n", "2", "-w", "1500", "8.8.8.8"], encoding="oem", errors="replace", timeout=15)
    ok_ip = "TTL=" in (r.stdout or "")
    try:
        urllib.request.urlopen("https://www.google.com/generate_204", timeout=6)
        ok_web = True
    except OSError:
        ok_web = False
    ms = re.findall(r"=(\d+)\s*мс|time[=<](\d+)ms", r.stdout or "")
    return ok_ip, ok_web, ms


# Инструменты для ИИ-плана: имя → (действие для политики, описание и аргументы)
TOOLS = {
    "command": ("open", "выполнить обычную команду Клодика текстом, например «открой steam», «сверни окна», "
                        "«напомни через 10 минут…»: {\"text\": \"...\"}"),
    "set_volume": ("volume", "громкость системы в процентах: {\"percent\": 30}"),
    "set_brightness": ("brightness", "яркость экрана (ноутбук) в процентах: {\"percent\": 60}"),
    "power_plan": ("change_system_settings", "схема питания: {\"plan\": \"balanced|high|saver\"}"),
    "theme": ("change_system_settings", "тема Windows: {\"mode\": \"dark|light\"}"),
    "install_app": ("install", "установить программу через winget: {\"name\": \"...\"}"),
    "uninstall_app": ("uninstall", "удалить программу через winget: {\"name\": \"...\"}"),
    "list_autostart": ("pc_info", "показать автозапуск (только показ): {}"),
    "clean_temp": ("delete_file", "убрать в корзину временные файлы старше 2 дней: {}"),
    "internet_check": ("pc_info", "проверить интернет и пинг: {}"),
    "flush_dns": ("network_changes", "сбросить кэш DNS: {}"),
    "powershell": ("shell", "команда PowerShell с объяснением (только если других инструментов нет): "
                            "{\"command\": \"...\", \"why\": \"...\"}"),
    "pc_summary": ("pc_info", "сводка по ПК: загрузка, память, диск, видеокарта: {}"),
}


def tool_action(name, args):
    """Категория для политики (для PowerShell — по самой команде: чтение сразу, опасное — с подтверждением)."""
    if name == "powershell":
        cmd = str(args.get("command", ""))
        if DANGER.search(cmd):
            return "anything_hard_to_undo"
        return "pc_info" if READONLY.match(cmd) else "shell"
    return TOOLS.get(name, ("anything_hard_to_undo",))[0]
