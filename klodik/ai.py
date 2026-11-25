"""Слой ИИ (раздел 4): один интерфейс, провайдеры взаимозаменяемы.
- Gemini (бесплатный API, ключ владельца в %APPDATA%\\Klodik\\.env) — для сложного: план, код, разбор ошибок, пересказ.
  Только обычный текст запроса: скриншоты, буфер, файлы, память и журнал в облако не уходят.
  Считаем запросы (запас под лимит), кэшируем повторы, при лимите/ошибке/без сети — сами на Ollama.
- Ollama (локально, без лимитов, офлайн) — всё личное, картинки, болтовня. Быстрая/умная/зрячая модели из .env."""
import base64
import hashlib

from .common import *  # noqa: F401,F403
from .brain import ollama_call, ollama_models, pick_model
from .voice import log_error

CACHE = os.path.join(DATA_DIR, "ai_cache.json")
USAGE = os.path.join(DATA_DIR, "ai_usage.json")
LIMIT_MIN, LIMIT_DAY = 8, 200                   # бесплатный тариф Gemini: держим запас под его лимиты
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"


def env():
    from .pet_onboard import read_env
    return read_env()


class AI:
    def __init__(s, local_only=lambda: False):
        s.local_only = local_only                  # режим «только локально» из меню
        s.where = "local"                          # что ответило последним: cloud/local — для значка
        try:
            s.cache = json.load(open(CACHE, encoding="utf-8"))
        except (OSError, ValueError):
            s.cache = {}
        try:
            s.usage = json.load(open(USAGE, encoding="utf-8"))
        except (OSError, ValueError):
            s.usage = {}
        s.minute = []

    # --- учёт лимитов Gemini ---
    def can_cloud(s):
        e = env()
        if s.local_only() or not e.get("GEMINI_API_KEY"):
            return False
        now = time.time()
        s.minute = [t for t in s.minute if now - t < 60]
        day = s.usage.get(time.strftime("%Y-%m-%d"), 0)
        return len(s.minute) < LIMIT_MIN and day < LIMIT_DAY

    def count_cloud(s):
        s.minute.append(time.time())
        k = time.strftime("%Y-%m-%d")
        s.usage = {k: s.usage.get(k, 0) + 1}         # храним только сегодня
        try:
            json.dump(s.usage, open(USAGE, "w", encoding="utf-8"))
        except OSError:
            pass

    # --- провайдеры ---
    def gemini(s, system, prompt, want_json, tokens):
        e = env()
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": system}]},
                "generationConfig": {"maxOutputTokens": tokens, "temperature": 0.7,
                                     **({"responseMimeType": "application/json"} if want_json else {})}}
        req = urllib.request.Request(GEMINI_URL.format(m=e.get("GEMINI_MODEL", "gemini-2.5-flash")),
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "x-goog-api-key": e["GEMINI_API_KEY"]})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
        return d["candidates"][0]["content"]["parts"][0]["text"].strip()

    def ollama(s, system, prompt, want_json, tokens, smart=True, image=None):
        e = env()
        models = ollama_models()
        if models is None:
            raise RuntimeError("Ollama не запущена")
        key = "OLLAMA_MODEL_VISION" if image else ("OLLAMA_MODEL_SMART" if smart else "OLLAMA_MODEL_FAST")
        want = e.get(key)
        model = want if want and any(m.startswith(want) for m in models) else pick_model(models)
        if not model:
            raise RuntimeError("нет моделей Ollama")
        msg = {"role": "user", "content": prompt}
        if image:
            msg["images"] = [base64.b64encode(open(image, "rb").read()).decode()]
        d = ollama_call("/api/chat", {"model": model, "stream": False, "keep_alive": "10m",
                                      **({"format": "json"} if want_json else {}),
                                      "options": {"num_predict": tokens, "temperature": 0.7},
                                      "messages": [{"role": "system", "content": system}, msg]}, 300)
        return d["message"]["content"].strip()

    def ask(s, system, prompt, task="chat", private=True, want_json=False, tokens=400, image=None):
        """Главный вход. private=True — только локально (личное, память, буфер, файлы, картинки).
        task: chat / plan / code / summarize / explain — для сложного (и не личного) пробуем Gemini."""
        cloud_ok = (not private and image is None and task in ("plan", "code", "summarize", "explain", "chat")
                    and s.can_cloud())
        key = hashlib.sha1(f"{task}|{system}|{prompt}".encode()).hexdigest()
        hit = s.cache.get(key)
        if hit and time.time() - hit["t"] < 86400 and task != "chat":   # повтор за сутки — из кэша
            s.where = hit["w"]
            return hit["a"]
        ans = None
        if cloud_ok:
            try:
                ans = s.gemini(system, prompt, want_json, tokens)
                s.count_cloud()
                s.where = "cloud"
            except (OSError, ValueError, KeyError, IndexError) as e:   # лимит 429, нет сети, сбой — идём локально
                log_error(f"Gemini: {e} — переключаюсь на Ollama")
        if ans is None:
            ans = s.ollama(system, prompt, want_json, tokens, smart=task != "fast", image=image)   # умная — на видеокарте быстро
            s.where = "local"
        if task != "chat":
            s.cache[key] = {"t": time.time(), "a": ans, "w": s.where}
            s.cache = dict(list(s.cache.items())[-300:])
            try:
                json.dump(s.cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
            except OSError:
                pass
        return ans


def parse_json(text):
    """Ответ модели → dict; модели иногда оборачивают JSON в ``` или пишут текст рядом."""
    try:
        return json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text or "", re.S)
        if m:
            try:
                return json.loads(m[0])
            except ValueError:
                pass
    return {"text": text}
