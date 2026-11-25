"""Что есть на компе: «Пуск», игры Steam/Epic, ярлыки; выученные фразы."""
from .common import *  # noqa: F401,F403

# ---------- приложения: панель MiniLauncher + меню «Пуск» ----------
def load_launcher():
    try:
        loader = importlib.machinery.SourceFileLoader("mini_launcher", LAUNCHER)
        mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("mini_launcher", loader))
        loader.exec_module(mod)
        with open(os.path.join(os.path.dirname(LAUNCHER), "apps.json"), encoding="utf-8") as f:
            return mod, json.load(f)
    except Exception:  # панели может не быть — Клодик живёт и без неё
        return None, []


APPS_CACHE = os.path.join(DATA_DIR, "apps_cache.json")
LEARNED = os.path.join(DATA_DIR, "learned.json")
CMD_WORDS = ("открой запусти включи закрой сверни разверни покажи громче тише погромче потише звук пауза "
             "следующий предыдущий найди загугли засеки напомни таймер минут минуту минуты секунд час часа через "
             "разгреби бульдозер все всё окна окно сфоткай скрин фотки позови прогони друга залезь слезь надень "
             "сними каску корону очки колпак шапку снег покорми мячик спать мне сюда комп слушай можешь запустить "
             "выключи пять десять двадцать тридцать").split()


def load_learned():
    try:
        return json.load(open(LEARNED, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_learned(d):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LEARNED, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def load_start_apps():
    """Программы из меню «Пуск» → [(имя, что запускать)]."""
    r = run_quiet(["powershell", "-NoProfile", "-Command",
                   "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-StartApps | Select Name,AppID | ConvertTo-Json -Compress"],
                  encoding="utf-8", errors="replace", timeout=60)
    try:
        data = json.loads(r.stdout)
        return [(d["Name"], "shell:AppsFolder\\" + d["AppID"]) for d in (data if isinstance(data, list) else [data])]
    except (ValueError, KeyError, TypeError):
        return []


def steam_games():
    """Установленные игры Steam: читаем libraryfolders.vdf и appmanifest_*.acf."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            root = winreg.QueryValueEx(k, "SteamPath")[0]
    except OSError:
        return []
    libs = {os.path.normpath(root)}
    try:
        with open(os.path.join(root, "steamapps", "libraryfolders.vdf"), encoding="utf-8", errors="replace") as f:
            libs |= {os.path.normpath(p.replace("\\\\", "\\")) for p in re.findall(r'"path"\s+"([^"]+)"', f.read())}
    except OSError:
        pass
    out = []
    for lib in libs:
        for acf in glob_files(os.path.join(lib, "steamapps"), "appmanifest_", ".acf"):
            try:
                txt = open(acf, encoding="utf-8", errors="replace").read()
                name, appid = re.search(r'"name"\s+"([^"]+)"', txt)[1], re.search(r'"appid"\s+"(\d+)"', txt)[1]
            except (OSError, TypeError):
                continue
            if not re.search(r"redistributable|proton|steamworks|steam linux|runtime", name, re.I):
                out.append((name, f"steam://rungameid/{appid}"))
    return out


def epic_games():
    out, d = [], r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests"
    for item in glob_files(d, "", ".item"):
        try:
            j = json.load(open(item, encoding="utf-8"))
            out.append((j["DisplayName"], "com.epicgames.launcher://apps/" + urllib.parse.quote(
                f"{j['CatalogNamespace']}:{j['CatalogItemId']}:{j['AppName']}") + "?action=launch&silent=true"))
        except (OSError, ValueError, KeyError):
            continue
    return out


def desktop_links():
    out = []
    for d in (special_dir(0x10), special_dir(0x19)):            # мой рабочий стол и общий
        for ext in (".lnk", ".url"):
            for f in glob_files(d, "", ext):
                out.append((os.path.splitext(os.path.basename(f))[0], f))
    return out


def glob_files(d, prefix, ext):
    try:
        return [os.path.join(d, f) for f in os.listdir(d) if f.startswith(prefix) and f.lower().endswith(ext)]
    except OSError:
        return []


def scan_apps():
    """Всё, что можно запустить: игры Steam/Epic, ярлыки рабочего стола, меню «Пуск». Кэшируется на диск."""
    games = steam_games() + epic_games()
    apps = games + desktop_links() + load_start_apps()
    seen, uniq = set(), []
    for name, tgt in apps:
        if name.lower() not in seen and not JUNK.search(name):
            seen.add(name.lower())
            uniq.append((name, tgt))
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(APPS_CACHE, "w", encoding="utf-8") as f:
            json.dump({"apps": uniq, "games": [g[0] for g in games]}, f, ensure_ascii=False)
    except OSError:
        pass
    return uniq, [g[0] for g in games]


def cached_apps():
    try:
        d = json.load(open(APPS_CACHE, encoding="utf-8"))
        return [tuple(x) for x in d["apps"]], d["games"]
    except (OSError, ValueError, KeyError):
        return [], []
