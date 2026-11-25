"""Политика доступа (раздел 3): что Клодик делает сам, что после «да», что после двойного подтверждения,
что запрещено всегда. Плюс журнал действий с причиной и удаление только в корзину."""
from .common import *  # noqa: F401,F403

PKG_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
POLICY_FILE = os.path.join(DATA_DIR, "policy.json")      # копия владельца — её можно править руками
JOURNAL = os.path.join(DATA_DIR, "journal.jsonl")
LEVELS = {"advisor": "Советник (только подсказывает)", "assistant": "Помощник (рекомендуется)",
          "autopilot": "Автопилот (белый список и расписание)"}
# действие Клодика → категория из policy.json
ACTION_CAT = {
    "open": "open_app", "url": "open_app", "open_file": "open_app", "open_folder": "open_app",
    "close": "close_app", "minimize": "close_app", "maximize": "close_app", "focus": "close_app",
    "dozer_minimize": "close_app", "dozer_close": "close_app",
    "lock": "close_app",                                   # заблокировать экран — безвредно, как свернуть всё
    "volume": "volume", "mute": "volume", "media": "volume",
    "screenshot": "screenshot", "timer": "timers", "note": "notes", "type_text": "notes",
    "find_file": "read_system_info", "space_report": "read_system_info", "pc_info": "read_system_info",
    "clip_explain": "explain", "clip_translate": "translate", "clip_fix": "translate",
    "shutdown": "shutdown_or_reboot", "restart": "shutdown_or_reboot", "sleep": "shutdown_or_reboot",
    "delete_file": "delete_or_move_files", "move_file": "delete_or_move_files",
    "install": "install_app", "uninstall": "uninstall_programs", "shell": "run_shell_command",
    "brightness": "brightness", "network_changes": "network_changes", "change_system_settings": "change_system_settings",
    "scheduled_tasks": "scheduled_tasks", "plugin_install": "anything_hard_to_undo",
    "registry": "registry", "network_reset": "network_reset", "format_disk": "format_or_partition_disks",
}


def load_policy():
    """Политика владельца; при первом запуске — копия стандартной из программы."""
    if not os.path.exists(POLICY_FILE):
        os.makedirs(DATA_DIR, exist_ok=True)
        shutil.copy2(os.path.join(PKG_DATA, "policy.json"), POLICY_FILE)
    try:
        return json.load(open(POLICY_FILE, encoding="utf-8"))
    except (OSError, ValueError):                          # файл испортили руками — работаем по стандартной
        return json.load(open(os.path.join(PKG_DATA, "policy.json"), encoding="utf-8"))


def decide(policy, level, action):
    """→ "auto" | "ask" | "double" | "forbidden" | "advise"."""
    cat = ACTION_CAT.get(action, action)
    if cat in policy.get("forbidden", []):
        return "forbidden"
    if level == "advisor":
        return "advise"
    if cat in policy.get("double_confirm", []):
        return "double"
    if cat in policy.get("auto", []):
        return "auto"
    return "ask"                                           # неизвестное — только после «да»


def journal(action, target, by, reason, result):
    """Одна строка журнала: что, над чем, кто попросил, зачем, чем кончилось. Секретов не пишем."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(JOURNAL, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "action": action, "target": str(target)[:120],
                                "by": by, "reason": str(reason)[:160], "result": str(result)[:120]},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass


def read_journal(n=200):
    try:
        lines = open(JOURNAL, encoding="utf-8").read().splitlines()[-n:]
        return [json.loads(l) for l in lines if l.strip()]
    except (OSError, ValueError):
        return []


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [("hwnd", wt.HWND), ("wFunc", wt.UINT), ("pFrom", wt.LPCWSTR), ("pTo", wt.LPCWSTR),
                ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wt.BOOL), ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", wt.LPCWSTR)]


def recycle(path):
    """Удалить ТОЛЬКО в корзину (можно вернуть). Если в корзину нельзя — исключение, навсегда не стираем."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    op = SHFILEOPSTRUCTW(None, 3, os.path.abspath(path) + "\0\0", None,
                         0x40 | 0x10 | 0x4 | 0x400 | 0x4000, False, None, None)   # ALLOWUNDO|NOCONFIRM|SILENT|NOERRORUI|WANTNUKEWARNING
    if ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) or os.path.exists(path):
        raise RuntimeError("в корзину не получилось — навсегда удалять не буду")
