"""Голос: «Клодик, …» через Vosk, журналы."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403

# ---------- голос: «Клодик, …» ----------
WAKE_EXTRA = set()          # как именно распознавалка слышит «Клодик» у этого человека (из подстройки), в латинице tr()
PROFILE = os.path.join(DATA_DIR, "voice_profile.json")


def load_profile():
    try:
        WAKE_EXTRA.update(json.load(open(PROFILE, encoding="utf-8")).get("wake", []))
    except (OSError, ValueError):
        pass


def save_profile():
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PROFILE, "w", encoding="utf-8") as f:
        json.dump({"wake": sorted(WAKE_EXTRA)}, f, ensure_ascii=False)


def wake_len(words):
    """Сколько первых слов — это «Клодик» (0 — не обращение). Модель слышит имя по-разному: «клади к», «клодия»,
    «колодок», «логик»… Одно слово целиком сверяем мягче, начало длинной фразы — строже."""
    skip = 1 if len(words) > 1 and words[0] in ("эй", "ну", "слушай", "а") else 0
    for n in ((2, 1) if len(words) > skip + 1 and len(words[skip + 1]) <= 3 else (1,)):
        part = words[skip:skip + n]
        joined = tr("".join(part))
        alone = len(words) == skip + n                 # человек сказал только имя
        if joined in WAKE_EXTRA or WAKE.match(" ".join(part)) or (   # «хладик», «владик» — ~0,67
                len(joined) >= 4 and difflib.SequenceMatcher(None, joined, "klodik").ratio() >= (0.6 if alone else 0.66)):
            return skip + n
    return 0


CALL_APPS = ("discord", "telegram", "zoom", "teams", "skype", "whatsapp", "viber")


def mic_users():
    """Кто сейчас держит микрофон — по журналу доступа Windows (LastUsedTimeStop == 0 значит «прямо сейчас»)."""
    base, out = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone", []
    for sub in ("", "\\NonPackaged"):
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, base + sub)
        except OSError:
            continue
        i = 0
        while True:
            try:
                name = winreg.EnumKey(k, i)
            except OSError:
                break
            i += 1
            try:
                with winreg.OpenKey(k, name) as sk:
                    if winreg.QueryValueEx(sk, "LastUsedTimeStop")[0] == 0 and winreg.QueryValueEx(sk, "LastUsedTimeStart")[0]:
                        out.append(name)
            except OSError:
                pass
    return out


def running(exe):
    r = run_quiet(["tasklist", "/fi", f"imagename eq {exe}", "/fo", "csv", "/nh"], encoding="oem", errors="replace",
                  timeout=10)
    return exe.lower() in (r.stdout or "").lower()


def in_call():
    """Discord/Telegram/Zoom… прямо сейчас держит микрофон (и правда запущен — Windows иногда забывает снять отметку)."""
    for u in mic_users():
        exe = u.replace("#", "\\").rsplit("\\", 1)[-1]
        if any(app in u.lower() for app in CALL_APPS) and running(exe if exe.lower().endswith(".exe") else exe + ".exe"):
            return True
    return False


VOICES = {"dmitri": "Дмитрий", "denis": "Денис", "ruslan": "Руслан", "irina": "Ирина (голос Windows)"}
PIPER_DIR = os.path.join(DATA_DIR, "piper")
PIPER_ZIP = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
PIPER_VOICE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/{v}/medium/ru_RU-{v}-medium{ext}"


def piper_exe():
    return os.path.join(PIPER_DIR, "piper", "piper.exe")


def piper_model(v):
    return os.path.join(PIPER_DIR, f"ru_RU-{v}-medium.onnx")


def download_piper(v):
    """Piper (офлайн-синтез речи, ~20 МБ) и голос (~60 МБ) — один раз."""
    import zipfile
    os.makedirs(PIPER_DIR, exist_ok=True)
    if not os.path.exists(piper_exe()):
        tmp = os.path.join(PIPER_DIR, "piper.zip")
        urllib.request.urlretrieve(PIPER_ZIP, tmp)
        with zipfile.ZipFile(tmp) as z:
            z.extractall(PIPER_DIR)
        os.remove(tmp)
    for ext in (".onnx.json", ".onnx"):
        dst = piper_model(v) + ext[5:]
        if not os.path.exists(dst):
            urllib.request.urlretrieve(PIPER_VOICE.format(v=v, ext=ext), dst + ".part")
            os.replace(dst + ".part", dst)
    cfg = piper_model(v) + ".json"                          # новые голоса знают английские дифтонги, а этот piper — нет
    j = json.load(open(cfg, encoding="utf-8"))
    bad = [k for k in j.get("phoneme_id_map", {}) if len(k) != 1]
    if bad:
        for k in bad:
            del j["phoneme_id_map"][k]
        json.dump(j, open(cfg, "w", encoding="utf-8"), ensure_ascii=False)


class Speaker:
    """Голос Клодика. Мужские нейроголоса Piper (офлайн, держим модель загруженной — фраза за ~0,3 с),
    запасной — встроенная Ирина из Windows. Пока говорит — speaking() = True, уши в это время закрыты."""
    SAPI = ("[Console]::InputEncoding=[Text.Encoding]::UTF8;Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "try{$s.SelectVoice('Microsoft Irina Desktop')}catch{};$s.Rate=1;$s.Volume=[int]$env:KV;"
            "while(($l=[Console]::In.ReadLine()) -ne $null){if($l){$s.Speak($l)};[Console]::Out.WriteLine('done')}")

    def __init__(s, voice="dmitri", volume=40):
        s.voice, s.q, s.pending, s.until, s.cancel = voice, queue.Queue(), 0, 0.0, threading.Event()
        s.volume = volume                                     # 0–100, громкость только голоса Клодика (не всей системы)
        s.piper = s.sapi = None
        s.piper_voice, s.fetching = None, False
        s.out = os.path.join(os.environ.get("TEMP", DATA_DIR), "klodik_voice")
        threading.Thread(target=s.worker, daemon=True).start()

    def set_voice(s, v):
        s.voice = v
        s.hush()

    def ready(s):
        return s.voice != "irina" and os.path.exists(piper_exe()) and os.path.exists(piper_model(s.voice) + ".json")

    def fetch(s):
        if s.fetching:
            return
        s.fetching = True

        def go():
            try:
                download_piper(s.voice)
            except Exception as e:  # нет интернета — говорим Ириной
                log_error(f"голос {s.voice} не скачался: {e}")
            s.fetching = False
        threading.Thread(target=go, daemon=True).start()

    def say(s, text):
        text = re.sub(r"[«»\"*♥…⏰]+", "", text).replace("\n", ". ").strip()
        if not text or s.pending >= 2:                       # не копим очередь — лучше пропустить фразу
            return
        s.pending += 1
        s.q.put(text)

    def worker(s):
        while True:
            text = s.q.get()
            s.cancel.clear()
            try:
                if s.voice != "irina" and not s.ready():
                    s.fetch()                                 # пока качается мужской голос — говорит Ирина
                s.speak_piper(text) if s.ready() else s.speak_sapi(text)
            except Exception as e:  # голос сломался — не роняем Клодика
                log_error(f"голос: {e}")
                s.piper = s.sapi = None
            finally:
                s.pending = max(0, s.pending - 1)
                s.until = time.time() + (0 if s.cancel.is_set() else 0.4)   # эхо из колонок ещё долетает до микрофона

    def speak_piper(s, text):
        import wave
        if not s.piper or s.piper.poll() is not None or s.piper_voice != s.voice:
            if s.piper and s.piper.poll() is None:
                s.piper.kill()
            os.makedirs(s.out, exist_ok=True)
            s.piper = subprocess.Popen([piper_exe(), "--model", piper_model(s.voice), "--output_dir", s.out],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                       creationflags=NOWIN)
            s.piper_voice = s.voice
        s.piper.stdin.write(text.encode("utf-8") + b"\n")
        s.piper.stdin.flush()
        wav = s.piper.stdout.readline().decode("utf-8", "replace").strip()   # piper печатает путь к готовому wav
        if not wav or not os.path.exists(wav):
            raise RuntimeError("piper не выдал звук")
        with wave.open(wav) as w:
            dur = w.getnframes() / w.getframerate()
        s.until = time.time() + dur + 0.4
        v = int(max(0, min(100, s.volume)) / 100 * 0xFFFF)  # громкость звука нашего процесса (как ползунок в микшере)
        ctypes.windll.winmm.waveOutSetVolume(None, v | (v << 16))
        winsound.PlaySound(wav, winsound.SND_FILENAME | winsound.SND_ASYNC)
        end = time.time() + dur
        while time.time() < end and not s.cancel.is_set():  # ждём, пока договорит (или hush оборвёт)
            time.sleep(0.05)
        try:
            os.remove(wav)
        except OSError:
            pass

    def speak_sapi(s, text):
        if not s.sapi or s.sapi.poll() is not None or getattr(s, "sapi_vol", None) != s.volume:
            if s.sapi and s.sapi.poll() is None:
                s.sapi.kill()
            s.sapi = subprocess.Popen(["powershell", "-NoProfile", "-Command", s.SAPI], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, creationflags=NOWIN, text=True, encoding="utf-8",
                                      env={**os.environ, "KV": str(int(s.volume))})
            s.sapi_vol = s.volume
        s.until = time.time() + 60
        s.sapi.stdin.write(text + "\n")
        s.sapi.stdin.flush()
        s.sapi.stdout.readline()                              # «done» — договорила
        s.until = 0.0

    def hush(s):
        """Замолчать прямо сейчас."""
        s.cancel.set()
        while not s.q.empty():
            try:
                s.q.get_nowait()
                s.pending = max(0, s.pending - 1)
            except queue.Empty:
                break
        winsound.PlaySound(None, winsound.SND_PURGE)
        if s.sapi and s.sapi.poll() is None:
            s.sapi.kill()
        s.sapi, s.until = None, 0.0

    def speaking(s):
        return s.pending > 0 or time.time() < s.until


class VoiceLogic:
    """Фразы из распознавалки → события: wake (услышал имя), heard (говоришь…), voice (команда после имени),
    voice_follow (команда в течение 20 с после прошлой — без повторного «Клодик»), voice_timeout, follow_end."""
    WAIT, FOLLOW = 8, 20

    def __init__(s):
        s.until, s.soft, s.mode, s.strict = 0.0, False, "", False   # strict: в звонке — без «20 с без имени»

    def partial(s, text, now):
        if not text:
            return []
        if s.until:
            s.until = max(s.until, now + 3)
            return [("heard", text)]
        w = text.split()
        n = wake_len(w)
        if not n:
            return []
        ev = [] if s.soft else [("wake",)]
        s.soft = True
        rest = " ".join(w[n:])
        return ev + ([("heard", rest)] if rest else [])

    def final(s, text, now):
        was_soft, s.soft = s.soft, False
        if not text:
            return []
        w = text.split()
        n = wake_len(w)
        rest = " ".join(w[n:])
        if s.until:                                    # уже слушаем: после «Клодик» или сразу после команды
            if len(rest) < 2:                          # «да»/«нет» на «точно?» — тоже ответ
                if n:
                    s.until, s.mode = now + s.WAIT, "wait"
                return []
            if s.mode == "follow" and not n and s.strict:      # в звонке фразы без имени — это друзьям, не мне
                return []
            kind = "voice_follow" if s.mode == "follow" and not n else "voice"
            s.until, s.mode = (0.0, "") if s.strict else (now + s.FOLLOW, "follow")
            return [(kind, rest)]
        if not n:
            return []
        if len(rest) >= 3:
            s.until, s.mode = (0.0, "") if s.strict else (now + s.FOLLOW, "follow")
            return [("voice", rest)]
        s.until, s.mode = now + s.WAIT, "wait"
        return [] if was_soft else [("wake",)]          # «Слушаю!» уже показали по ходу фразы

    def tick(s, now):
        if s.until and now > s.until:
            s.until = 0.0
            return [("voice_timeout" if s.mode == "wait" else "follow_end",)]
        return []


VOSK_BIG = "vosk-model-ru-0.42"                      # большая модель: точнее, ~1,8 ГБ, ставится по желанию


def vosk_dir():
    big = os.path.join(DATA_DIR, VOSK_BIG)
    return big if os.path.isdir(big) else os.path.join(DATA_DIR, VOSK_MODEL)


ERRLOG = os.path.join(DATA_DIR, "errors.log")


def log_error(text):
    """Журнал ошибок %APPDATA%\\Klodik\\errors.log (последние ~500 строк) — чтобы потом починить."""
    path = ERRLOG
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        old = open(path, encoding="utf-8").read().splitlines()[-499:] if os.path.exists(path) else []
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(old + [time.strftime("%m-%d %H:%M:%S ") + text.rstrip()]) + "\n")
    except OSError:
        pass


def log_voice(text):
    """Что услышал рядом с «Клодик» — в %APPDATA%\\Klodik\\voice.log (последние ~300 строк), чтобы подстроить уши."""
    path = os.path.join(DATA_DIR, "voice.log")
    try:
        lines = open(path, encoding="utf-8").read().splitlines()[-299:] if os.path.exists(path) else []
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines + [time.strftime("%m-%d %H:%M:%S ") + text]) + "\n")
    except OSError:
        pass


def download_vosk():
    import zipfile
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = os.path.join(DATA_DIR, "vosk.zip")
    urllib.request.urlretrieve(VOSK_URL, tmp)
    with zipfile.ZipFile(tmp) as z:
        z.extractall(DATA_DIR)                          # extractall отбрасывает «..» и абсолютные пути
    os.remove(tmp)


VK_RCONTROL = 0xA3                                   # «кнопка говорить» — правый Ctrl


class Listener:
    """Микрофон → Vosk (всё на компе, офлайн) → события в очередь Клодика.
    Сразу слушает маленькой моделью (грузится за секунду), большую подгружает в фоне (~2 мин) и подменяет на лету.
    Глохнет, пока Клодик сам говорит (muted) и пока ты в звонке Discord/Telegram. Правый Ctrl — говорить без имени.
    calib=True — режим подстройки: все фразы отдаются как есть событием «calib»."""
    def __init__(s, out, muted=lambda: False):
        s.out, s.muted, s.stop_ev, s.calib = out, muted, threading.Event(), False
        s.rec, s.big_rec = None, None
        threading.Thread(target=s.run, daemon=True).start()

    def stop(s):
        s.stop_ev.set()

    def emit(s, ev):
        for e in ev:
            s.out.put((e[0], e[1] if len(e) > 1 else ""))

    def load_big(s, vosk):
        try:
            s.big_rec = vosk.KaldiRecognizer(vosk.Model(os.path.join(DATA_DIR, VOSK_BIG)), 16000)
            s.out.put(("info", "Большие уши готовы — теперь слышу лучше."))
        except Exception as e:  # битая модель — остаёмся на маленькой
            log_error(f"большая модель речи не загрузилась: {e}")

    def run(s):
        try:
            import sounddevice as sd
            import vosk
        except ImportError:
            return s.out.put(("info", "Для голоса не хватает пакетов vosk и sounddevice"))
        small = os.path.join(DATA_DIR, VOSK_MODEL)
        if not os.path.isdir(small):
            s.out.put(("info", "Качаю «уши» — русскую модель речи (45 МБ, один раз)…"))
            try:
                download_vosk()
            except Exception as e:  # нет интернета и т. п.
                return s.out.put(("info", f"Не скачались уши: {e}"))
        vosk.SetLogLevel(-1)
        s.rec = vosk.KaldiRecognizer(vosk.Model(small), 16000)
        if os.path.isdir(os.path.join(DATA_DIR, VOSK_BIG)):
            threading.Thread(target=s.load_big, args=(vosk,), daemon=True).start()
        logic, q = VoiceLogic(), queue.Queue()
        ptt, buf, deaf, call, next_call = False, [], False, False, 0.0
        try:
            with sd.RawInputStream(samplerate=16000, blocksize=2000, dtype="int16", channels=1,
                                   callback=lambda data, frames, t, status: q.put(bytes(data))):
                s.out.put(("info", "Слушаю! Скажи «Клодик» — и команду. Или зажми правый Ctrl и говори."))
                while not s.stop_ev.is_set():
                    try:
                        data = q.get(timeout=0.5)
                    except queue.Empty:
                        data = None
                    now = time.time()
                    if s.big_rec and not ptt:                 # подмена на большую модель — между фразами
                        s.rec, s.big_rec = s.big_rec, None
                    if now >= next_call:
                        next_call = now + 3
                        c = in_call()
                        if c != call:
                            call = logic.strict = c
                            s.out.put(("info", "Ты в звонке — отзываюсь только на «Клодик»." if c
                                       else "Звонок закончился — снова слушаю как обычно."))
                    down = bool(u32.GetAsyncKeyState(VK_RCONTROL) & 0x8000)
                    if s.muted() and not down and not ptt:    # говорю сам — уши закрыты, чтобы не слышать себя
                        if not deaf:
                            deaf = True
                            s.rec.Reset()
                        continue
                    deaf = False
                    ev = logic.tick(now)
                    if down and not ptt:                      # нажал правый Ctrl
                        ptt, buf = True, []
                        s.rec.Reset()
                        ev.append(("wake",))
                    if data is not None:
                        if s.rec.AcceptWaveform(data):
                            text = json.loads(s.rec.Result()).get("text", "").strip()
                            if s.calib:
                                ev.append(("calib", text)) if text else None
                            elif ptt:
                                buf.append(text)
                            else:
                                ev += logic.final(text, now)
                            if text and (logic.until or ptt or wake_len(text.split()) or
                                         difflib.SequenceMatcher(None, tr(text.split()[0]), "klodik").ratio() > 0.5):
                                log_voice(text)               # только обращения и почти-обращения — для настройки
                        else:
                            part = json.loads(s.rec.PartialResult()).get("partial", "").strip()
                            if s.calib:
                                ev.append(("calib_partial", part)) if part else None
                            elif ptt:
                                ev.append(("heard", " ".join(buf + [part]).strip())) if part or buf else None
                            else:
                                ev += logic.partial(part, now)
                    if ptt and not down:                      # отпустил — всё сказанное и есть команда
                        ptt = False
                        words = " ".join(buf + [json.loads(s.rec.FinalResult()).get("text", "")]).split()
                        text = " ".join(words[wake_len(words):])
                        ev.append(("voice", text) if text else ("voice_timeout",))
                        logic.until, logic.mode = now + logic.FOLLOW, "follow"
                    s.emit(ev)
        except Exception as e:  # нет микрофона, занят и т. п.
            s.out.put(("info", f"Микрофон не работает: {e}"))
            log_error(traceback.format_exc())
