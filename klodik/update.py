"""Автообновление Klodik.exe с GitHub Releases. Адрес — в UPDATE_REPO (или %APPDATA%\\Klodik\\update.json:
{"repo": "имя/репозиторий"}). Пока он пустой — обновления выключены."""
from .common import *  # noqa: F401,F403

VERSION = "1.7.0"
UPDATE_REPO = "mrkolobokonline-dev/klodik"           # отсюда (Releases) Клодики друзей берут новые версии


def repo():
    try:
        return json.load(open(os.path.join(DATA_DIR, "update.json"), encoding="utf-8")).get("repo") or UPDATE_REPO
    except (OSError, ValueError):
        return UPDATE_REPO


def ver(t):
    return tuple(int(x) for x in re.findall(r"\d+", t)[:3])


def find_update():
    """→ (версия, ссылка на Klodik.exe), если на GitHub есть версия новее, иначе None."""
    r = repo()
    if not (FROZEN and r):
        return None
    req = urllib.request.Request(f"https://api.github.com/repos/{r}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "Klodik-updater"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            rel = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:                                 # релизов ещё нет — значит и обновлять нечем
            return None
        raise
    tag = rel.get("tag_name", "")
    exe = next((a["browser_download_url"] for a in rel.get("assets", []) if a["name"].lower().endswith(".exe")), None)
    return (tag, exe) if exe and ver(tag) > ver(VERSION) else None


def install_update(url):
    """Качаем новую версию рядом, проверяем, что это exe, и меняем файл, когда старый Клодик закроется."""
    exe = os.path.join(INSTALL_DIR, "Klodik.exe")
    new = os.path.join(INSTALL_DIR, "Klodik.new.exe")
    urllib.request.urlretrieve(url, new)
    with open(new, "rb") as f:
        if f.read(2) != b"MZ" or os.path.getsize(new) < 5 * 2**20:   # не exe или оборванная загрузка
            os.remove(new)
            raise RuntimeError("скачался не тот файл")
    old, ok = os.path.join(INSTALL_DIR, "Klodik.old.exe"), OK_FLAG
    script = os.path.join(DATA_DIR, "update.cmd")
    # заменить → запустить → если за 60 с новая версия не отметилась «живу», вернуть старую
    with open(script, "w", encoding="cp866", errors="replace") as f:
        f.write(f'@echo off\r\ntaskkill /f /im Klodik.exe >nul 2>&1\r\ntimeout /t 2 /nobreak >nul\r\n'
                f'del "{ok}" >nul 2>&1\r\nmove /y "{exe}" "{old}" >nul\r\nmove /y "{new}" "{exe}" >nul\r\n'
                f'start "" "{exe}"\r\ntimeout /t 60 /nobreak >nul\r\n'
                f'if not exist "{ok}" (\r\n  taskkill /f /im Klodik.exe >nul 2>&1\r\n  timeout /t 2 /nobreak >nul\r\n'
                f'  move /y "{old}" "{exe}" >nul\r\n  start "" "{exe}"\r\n)\r\n')
    subprocess.Popen(["cmd", "/c", script], creationflags=NOWIN | 0x8)


OK_FLAG = os.path.join(DATA_DIR, "update_ok.flag")


def mark_alive():
    """Новая версия проработала 20 с — значит, запускается; откат не нужен."""
    try:
        open(OK_FLAG, "w").write(VERSION)
    except OSError:
        pass
