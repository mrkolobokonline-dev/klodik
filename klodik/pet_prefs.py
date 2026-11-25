"""Переключатели функций (каждая отдельно в меню), тихие часы, резервные копии данных."""
import zipfile

from .common import *  # noqa: F401,F403
from .pet_tasks import read_json, write_json

# функция → (название в меню, включена по умолчанию). Ресурсоёмкое и приватное — выключено по умолчанию.
FEATURES = {
    "walk_talk": ("Болтать на прогулке", True), "hints": ("Подсказки и забота (перерыв, вода, сон)", True),
    "climb": ("Прыгать по окнам", True), "dance": ("Танцевать под музыку", True),
    "eyes": ("Следить глазами за курсором", True), "morning": ("Утренняя сводка", True),
    "diary": ("Итоги дня и ночное самообучение", True), "learn_facts": ("Запоминать факты о тебе из болтовни", True),
    "game_talk": ("Комментировать игры и напоминать про дейлики", True), "updates": ("Автообновление", True),
}
BACKUP_DIR = os.path.join(DATA_DIR, "backup")
BACKUP_FILES = ("state.json", "memory.json", "learned.json", "reminders.json", "notes.json", "modes.json", "diary.json",
                "day.json", "phrases.json", "voice_profile.json", "policy.json", "onboarding.json", "journal.jsonl",
                "apps_cache.json")


def make_backup(dst):
    """Zip с данными Клодика (без моделей, голосов и секретов .env)."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for name in BACKUP_FILES:
            p = os.path.join(DATA_DIR, name)
            if os.path.exists(p):
                z.write(p, name)
    return dst


class PetPrefs:
    def on(s, feature):
        return feature not in s.prefs.get("off", []) if FEATURES[feature][1] else feature in s.prefs.get("on", [])

    def toggle(s, feature, value):
        off, on = set(s.prefs.get("off", [])), set(s.prefs.get("on", []))
        (on.add if value else on.discard)(feature)
        (off.discard if value else off.add)(feature)
        s.prefs["off"], s.prefs["on"] = sorted(off), sorted(on)
        s.save()
        if hasattr(s, "log"):
            s.log("feature", FEATURES[feature][0], "включил" if value else "выключил")

    def feature_menu(s, parent):
        m = tk.Menu(parent, tearoff=0)
        s.feat_vars = {}
        for k, (title, _) in FEATURES.items():
            v = s.feat_vars[k] = tk.BooleanVar(value=s.on(k))
            m.add_checkbutton(label=title, variable=v, command=lambda k=k, v=v: s.toggle(k, v.get()))
        m.add_separator()
        for key, title, options in (
                ("anim", "Анимации", [("max", "Максимум"), ("moderate", "Умеренно"), ("min", "Минимум")]),
                ("emo", "Эмоции", [("calm", "Спокойный"), ("lively", "Живой"), ("very", "Очень эмоциональный")]),
                ("game_mode", "В игре", [("hide", "Прятаться"), ("corner", "Тихо сидеть в углу")])):
            sub = tk.Menu(m, tearoff=0)
            var = tk.StringVar(value=s.prefs.get(key, options[0][0] if key != "emo" else "lively"))
            s.feat_vars[key] = var
            for val, label in options:
                sub.add_radiobutton(label=label, value=val, variable=var,
                                    command=lambda key=key, var=var: s.set_pref(key, var.get()))
            m.add_cascade(label=title, menu=sub)
        for key, title in (("no_emotions", "Режим без эмоций"), ("working", "Режим «я работаю»"),
                           ("local_only", "ИИ: только локально (без облака)")):
            v = s.feat_vars[key] = tk.BooleanVar(value=bool(s.prefs.get(key)))
            m.add_checkbutton(label=title, variable=v, command=lambda key=key, v=v: s.set_pref(key, v.get()))
        return m

    def set_pref(s, key, value):
        s.prefs[key] = value
        s.save()
        s.key = None
        if hasattr(s, "log"):
            s.log("setting", key, str(value))

    def quiet_now(s):
        """Тихие часы: «23:00–08:00» переходит через полночь."""
        q = s.prefs.get("quiet")
        if not q:
            return False
        try:
            a, b = [int(x.split(":")[0]) * 60 + int(x.split(":")[1]) for x in q]
        except (ValueError, IndexError):
            return False
        t = time.localtime()
        now = t.tm_hour * 60 + t.tm_min
        return a <= now < b if a < b else (now >= a or now < b)

    def daily_backup(s):
        """Раз в день копия данных в %APPDATA%\\Klodik\\backup, хранится 7 последних."""
        dst = os.path.join(BACKUP_DIR, time.strftime("klodik-%Y-%m-%d.zip"))
        if os.path.exists(dst):
            return
        try:
            make_backup(dst)
            old = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("klodik-"))[:-7]
            for f in old:
                os.remove(os.path.join(BACKUP_DIR, f))     # свои старые копии — можно, это не файлы владельца
        except OSError as e:
            log_error(f"резервная копия: {e}")

    def export_data(s):
        path = make_backup(os.path.join(special_dir(0x05) or HERE, time.strftime("Klodik-данные-%Y-%m-%d.zip")))
        s.say("Сохранил все мои данные в «Документы» (без ключей и моделей).", 4, speak=True)
        return path
