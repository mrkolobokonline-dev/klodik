"""Окно «Загрузки Клодика»: прогресс скачивания Ollama, модели ИИ и большой модели речи. Само закрывается, когда всё готово."""
import glob, json, os, threading, time, tkinter as tk, urllib.request
from tkinter import ttk

DATA = os.path.join(os.environ["APPDATA"], "Klodik")
OLLAMA_DIR = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Ollama")
VOSK_URL = "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"
MODEL = "qwen2.5:7b"
BG, CARD, FG, DIM, ACC = "#1f1f1f", "#2b2b2b", "#f3f3f3", "#a8a8a8", "#d97757"


def size_mb(path):
    try:
        return os.path.getsize(path) / 2**20
    except OSError:
        return 0.0


class Row:
    def __init__(s, parent, title):
        f = tk.Frame(parent, bg=CARD, padx=14, pady=10)
        f.pack(fill="x", pady=5)
        s.t = tk.Label(f, text=title, bg=CARD, fg=FG, font=("Segoe UI Variable Text", 11, "bold"), anchor="w")
        s.t.pack(fill="x")
        s.bar = ttk.Progressbar(f, length=380, maximum=100, style="K.Horizontal.TProgressbar")
        s.bar.pack(fill="x", pady=(6, 3))
        s.info = tk.Label(f, text="ждём…", bg=CARD, fg=DIM, font=("Segoe UI", 9), anchor="w")
        s.info.pack(fill="x")
        s.done = False

    def set(s, pct, text, done=False):
        s.bar["value"] = max(0, min(100, pct))
        s.info.config(text=text, fg="#6ccb5f" if done else DIM)
        s.done = done


class App:
    def __init__(s):
        s.root = tk.Tk()
        s.root.title("Загрузки Клодика")
        s.root.configure(bg=BG, padx=16, pady=12)
        s.root.attributes("-topmost", True)
        s.root.resizable(False, False)
        st = ttk.Style()
        st.theme_use("clam")
        st.configure("K.Horizontal.TProgressbar", troughcolor="#3a3a3a", background=ACC, bordercolor=CARD,
                     lightcolor=ACC, darkcolor=ACC, thickness=10)
        tk.Label(s.root, text="Что качает Клодик", bg=BG, fg=FG, font=("Segoe UI Variable Display", 14, "bold"),
                 anchor="w").pack(fill="x")
        s.r_app = Row(s.root, "Ollama — программа для ИИ на компе")
        s.r_model = Row(s.root, f"Мозги: модель {MODEL} (~4,7 ГБ)")
        s.r_ears = Row(s.root, "Большие уши: модель речи vosk-ru-0.42 (~1,8 ГБ)")
        s.vosk_total = None
        s.pull = {"pct": 0.0, "text": "ждём установку Ollama…", "done": False}
        threading.Thread(target=s.vosk_head, daemon=True).start()
        threading.Thread(target=s.watch_pull, daemon=True).start()
        s.tick()
        s.root.mainloop()

    def vosk_head(s):
        try:
            req = urllib.request.Request(VOSK_URL, method="HEAD")
            with urllib.request.urlopen(req, timeout=15) as r:
                s.vosk_total = int(r.headers["Content-Length"]) / 2**20
        except (OSError, ValueError, TypeError):
            s.vosk_total = 1890.0

    def watch_pull(s):
        """Как только Ollama ответит — подписываемся на ту же загрузку модели и читаем проценты."""
        while not s.pull["done"]:
            try:
                with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as r:
                    names = [m["name"] for m in json.load(r).get("models", [])]
                if any(n.startswith(MODEL) for n in names):
                    s.pull.update(pct=100, text="готово ✓", done=True)
                    return
                body = json.dumps({"model": MODEL, "stream": True}).encode()
                req = urllib.request.Request("http://127.0.0.1:11434/api/pull", data=body,
                                            headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=3600) as r:
                    for line in r:
                        d = json.loads(line)
                        tot, comp = d.get("total"), d.get("completed")
                        if tot and comp is not None:
                            s.pull.update(pct=100 * comp / tot,
                                          text=f"{comp / 2**30:.2f} из {tot / 2**30:.2f} ГБ · {d.get('status', '')[:30]}")
                        elif d.get("status") == "success":
                            s.pull.update(pct=100, text="готово ✓", done=True)
                            return
                        else:
                            s.pull["text"] = d.get("status", "")[:60]
            except (OSError, ValueError):
                time.sleep(3)

    def tick(s):
        # 1) программа Ollama: установлена? иначе — сколько скачал winget
        if os.path.exists(os.path.join(OLLAMA_DIR, "ollama.exe")):
            s.r_app.set(100, "установлена ✓", True)
        else:
            parts = glob.glob(os.path.join(os.environ["TEMP"], "WinGet", "Ollama*", "*"))
            mb = sum(size_mb(p) for p in parts)
            s.r_app.set(min(95, mb / 12), f"скачано {mb:.0f} МБ (~1,2 ГБ), потом установка" if mb else "готовлю загрузку…")
        # 2) модель ИИ — из потока Ollama
        s.r_model.set(s.pull["pct"], s.pull["text"], s.pull["done"])
        # 3) большая модель речи
        if os.path.isdir(os.path.join(DATA, "vosk-model-ru-0.42")) and not os.path.exists(os.path.join(DATA, "vosk-big.zip")):
            s.r_ears.set(100, "готово ✓", True)
        else:
            mb, tot = size_mb(os.path.join(DATA, "vosk-big.zip")), s.vosk_total or 1890.0
            s.r_ears.set(100 * mb / tot, f"{mb:.0f} из {tot:.0f} МБ" + (" · распаковка…" if mb >= tot * 0.99 else ""))
        if s.r_app.done and s.r_model.done and s.r_ears.done:
            tk.Label(s.root, text="Всё скачано! Окно закроется само.", bg=BG, fg="#6ccb5f",
                     font=("Segoe UI", 10)).pack(pady=(6, 0))
            s.root.after(8000, s.root.destroy)
            return
        s.root.after(1000, s.tick)


if __name__ == "__main__":
    App()
