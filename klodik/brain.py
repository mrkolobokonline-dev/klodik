"""Мозги: Ollama на компе, Claude по желанию."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403

def claude_exe():
    exe = os.path.join(os.environ.get("USERPROFILE", ""), ".local", "bin", "claude.exe")
    return exe if os.path.exists(exe) else shutil.which("claude")


def ollama_exe():
    p = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama")
    return next((os.path.join(p, f) for f in ("ollama app.exe", "ollama.exe") if os.path.exists(os.path.join(p, f))),
                None)


def want_model():
    """Какую модель качать: при 16+ ГБ памяти — умную 7b (~4,7 ГБ), иначе лёгкую 3b (~2 ГБ)."""
    m = MEMSTAT()
    m.len = ctypes.sizeof(MEMSTAT)
    k32.GlobalMemoryStatusEx(ctypes.byref(m))
    return OLLAMA_MODELS[0] if m.total >= 15 * 2**30 else OLLAMA_MODELS[1]


def pick_model(models):
    """Лучшая из скачанных: сначала наши qwen, потом любая другая."""
    for want in OLLAMA_MODELS:
        hit = next((m for m in models if m.startswith(want)), None)
        if hit:
            return hit
    return models[0] if models else None


def ollama_models():
    """Список моделей Ollama или None, если Ollama не запущена."""
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=1.5) as r:
            return [m["name"] for m in json.load(r).get("models", [])]
    except (OSError, ValueError, KeyError):
        return None


def ollama_call(path, body, timeout):
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def ask_ollama(prompt, model, system=None):
    d = ollama_call("/api/chat", {"model": model, "stream": False, "keep_alive": "10m",   # 10 мин держит в памяти
                                  "options": {"num_predict": 150, "temperature": 0.7},
                                  "messages": [{"role": "system", "content": system or SYSTEM},
                                               {"role": "user", "content": prompt}]}, 180)
    return d["message"]["content"].strip()


def ask_claude(prompt):
    exe = claude_exe() or "claude"
    # haiku: быстро и бережёт лимит; инструменты выключены — тут только болтовня
    r = run_quiet([exe, "-p", "--model", "haiku", "--tools", "", "--no-session-persistence", "--system-prompt", SYSTEM],
                  input=prompt, encoding="utf-8", errors="replace", timeout=120, cwd=HERE)
    out = (r.stdout or "").strip()
    if r.returncode or not out:
        err = (r.stderr or r.stdout or "нет ответа").strip().splitlines() or ["нет ответа"]
        raise RuntimeError(err[-1][:120])
    return out
