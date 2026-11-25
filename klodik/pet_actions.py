"""Бульдозер и задания «добежать → сделать»."""
from .common import *  # noqa: F401,F403
from .apps import *  # noqa: F401,F403
from .winapi import *  # noqa: F401,F403
from .monitor import *  # noqa: F401,F403
from .brain import *  # noqa: F401,F403
from .voice import *  # noqa: F401,F403
from .sprites import *  # noqa: F401,F403

from . import common  # noqa: E402


class PetActions:
    # --- бульдозер ---
    def start_dozer(s, mode):
        if s.busy:
            return s.say("Погоди, я занят…", 2)
        targets = []
        for w in s.windows():
            if w["proc"].lower() in SAFE_PROCS or "diablo" in w["title"].lower():
                continue
            if w["min"]:
                if mode == "close":
                    targets.append({"w": w, "st": "later"})
                continue
            l, t, r, b = w["rect"]
            targets.append({"w": w, "st": "wait", "l": l, "t": t, "max": w["max"] or r - l >= s.R - s.L - 20})
        if not targets:
            return s.say("Тут и так чисто!", 2)
        action = "dozer_close" if mode == "close" else "dozer_minimize"
        if s.decide(action) != "auto" and not getattr(s, "dozer_ok", False):
            def go():
                s.dozer_ok = True
                s.start_dozer(mode)
                s.dozer_ok = False
            return s.gate(action, f"{'закрыть' if mode == 'close' else 'свернуть'} {len(targets)} окон бульдозером", go)
        s.dz = {"mode": mode, "targets": sorted(targets, key=lambda d: d.get("l", 0)), "n": 0}
        s.drop()
        s.bubble.hide()
        if s.inp:
            s.close_input()
        s.state, s.dir = "dozer_out", -1
        s.say("Вызываю технику!", 2)

    def dz_act(s, tg):
        try:
            (s.fx.close if s.dz["mode"] == "close" else s.fx.minimize)(tg["w"]["hwnd"])
            s.dz["n"] += 1
        except Exception:  # окно уже закрылось само
            pass
        tg["st"] = "done"

    def dozer_update(s, dt):
        d = s.dozer
        d.step(dt, s.clock)
        blade = d.blade()
        s.x, s.y = d.x + 55, float(s.B - H)              # облачко над кабиной
        for tg in s.dz["targets"]:
            if tg["st"] == "wait":
                r = tg["w"]["rect"][2]
                if tg["max"]:
                    if blade >= (tg["l"] + r) / 2:
                        s.dz_act(tg)
                elif blade >= tg["l"]:
                    tg["st"], tg["x0"] = "push", blade
            if tg["st"] == "push":
                try:
                    s.fx.move(tg["w"]["hwnd"], blade, tg["t"])
                except Exception:
                    pass
                if blade - tg["x0"] > 170 or blade > s.R - 60:
                    s.dz_act(tg)
        if d.x > s.R + 10:
            for tg in s.dz["targets"]:
                if tg["st"] != "done":
                    s.dz_act(tg)
            d.destroy()
            n, closed = s.dz["n"], s.dz["mode"] == "close"
            s.log("dozer_close" if closed else "dozer_minimize", f"{n} окон", "сделано")
            if not closed:                                # свёрнутые окна можно вернуть: «верни как было»
                hw = [tg["w"]["hwnd"] for tg in s.dz["targets"] if tg["st"] == "done"]
                s.push_undo(f"{n} окон", lambda hw=hw: [s.fx.restore(h) for h in hw])
            s.dozer = s.dz = None
            s.state, s.timer = "idle", 2
            s.x, s.y, s.vy = float(s.R - W - 60), float(s.T + 40), 0.0
            word = "окно" if n % 10 == 1 and n % 100 != 11 else "окна" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "окон"
            s.say(f"Чисто! {'Закрыл' if closed else 'Свернул'} {n} {word}", 4)
            s.emote("pride", "medium")

    # --- действия ---
    def icon_for(s, app):
        if not (s.lmod and app):
            return None
        if app["id"] not in s.icons:
            try:
                s.icons[app["id"]] = tk.PhotoImage(file=s.lmod.icon_file(app)).subsample(2)
            except (tk.TclError, KeyError):
                s.icons[app["id"]] = None
        return s.icons[app["id"]]

    def resolve(s, name):
        n = (name or "").strip().lower()
        if not n:
            return None
        if n in DIRECT:
            return DIRECT[n], name, None
        n = ALIAS.get(n, n)
        if n in URLS:
            return URLS[n], name, None
        best, score = None, 0.0
        for app in s.apps:
            sc = max(match(n, app["name"]), match(n, app["id"]))
            t = s.lmod.target(app) if s.lmod and sc > score else None
            if t:
                best, score = (t, app["name"], s.icon_for(app)), sc
        for nm, tgt in s.start_apps:                       # «Пуск», игры Steam/Epic, ярлыки рабочего стола
            sc = match(n, nm) - 0.01                       # при равенстве — ярлык из панели
            if sc > score:
                best, score = (tgt, nm, None), sc
        return best if score >= 0.75 else None

    def describe(s, a):
        do = a.get("do")
        if do in ("close", "minimize", "maximize", "focus"):
            w = s.snap.get(a.get("win"), {}) if isinstance(a.get("win"), int) else {}
            verb = {"close": "закрыть", "minimize": "свернуть", "maximize": "развернуть", "focus": "показать"}[do]
            return f"{verb} окно «{w.get('title', '?')[:40]}»"
        return {"open": f"открыть {a.get('app')}", "url": f"открыть сайт {a.get('url', '')[:60]}",
                "volume": "поменять громкость", "mute": "выключить/включить звук", "media": "управлять музыкой"}.get(do, do)

    def plan(s, actions, gated=False):
        """Превращает команды в задания с анимацией: добежать → сделать. Всё проходит политику доступа."""
        jobs, sx = [], max(s.L + W / 2, min(s.start_x, s.R - W / 2))
        for a in actions:
            do = a.get("do")
            if not gated and s.decide(do) != "auto":          # не «сам» — спросить/запретить/подсказать
                s.gate(do, s.describe(a), lambda a=a: s.plan([a], gated=True))
                continue
            if do in ("close", "minimize", "maximize", "focus"):
                try:
                    w = s.snap[int(a.get("win"))]
                except (KeyError, TypeError, ValueError):
                    s.say("Не понял, какое окно", 3)
                    continue
                l, t, r, b = w["rect"]
                x = sx if w["min"] else max(s.L + W / 2, min((l + r) / 2, s.R - W / 2))
                h, title = w["hwnd"], w["title"][:40]
                fn, msg = {"close": (s.fx.close, "Закрыл"), "minimize": (s.fx.minimize, "Свернул"),
                           "maximize": (s.fx.maximize, "Развернул"), "focus": (s.fx.focus, "Вот оно")}[do]
                undo = (lambda h=h: s.fx.restore(h)) if do in ("minimize", "maximize") else None
                jobs.append({"x": x, "anim": "jump" if do in ("close", "maximize") else "dig", "action": do,
                             "target": title, "undo": undo,
                             "run": lambda fn=fn, h=h, m=f"{msg}: «{title}»": (fn(h), m)[1]})
            elif do == "open":
                res = s.resolve(a.get("app"))
                if not res:
                    s.say(f"Не нашёл «{a.get('app')}»", 3)
                    continue
                tgt, label, icon = res
                jobs.append({"x": sx, "anim": "dig", "icon": icon, "action": "open", "target": label,
                             "run": lambda tgt=tgt, label=label: (s.fx.start(tgt), f"Запускаю {label}!")[1]})
            elif do == "url":
                url = str(a.get("url", ""))
                if not url.startswith(("http://", "https://")):
                    continue
                jobs.append({"x": sx, "anim": "dig", "action": "url", "target": url,
                             "run": lambda url=url: (s.fx.start(url), "Открываю в браузере")[1]})
            elif do in ("volume", "mute", "media"):
                if do == "volume":
                    step = max(-10, min(10, int(a.get("step", 0))))
                    vk, n, m = (0xAF if step > 0 else 0xAE), abs(step), f"Громкость {'+' if step > 0 else '−'}{abs(step) * 2}%"
                elif do == "mute":
                    vk, n, m = 0xAD, 1, "Звук: щёлк"
                else:
                    vk = {"play": 0xB3, "next": 0xB0, "prev": 0xB1}.get(a.get("key"), 0xB3)
                    n, m = 1, "Музыка: есть!"
                if n:
                    back = {0xAF: 0xAE, 0xAE: 0xAF, 0xAD: 0xAD, 0xB3: 0xB3}.get(vk)   # обратное действие для отката
                    jobs.append({"x": None, "anim": "dance", "action": do, "target": m,
                                 "undo": (lambda b=back, n=n: s.fx.keys(b, n)) if back else None,
                                 "run": lambda vk=vk, n=n, m=m: (s.fx.keys(vk, n), m)[1]})
        s.jobs += jobs
        if not s.job:
            s.next_job()

    def next_job(s):
        s.job = s.jobs.pop(0) if s.jobs else None
        if s.job:
            s.drop()
            s.state, s.job_phase, s.job_t, s.job_fired = "job", "go", 0.0, False
        elif s.state == "job":
            s.state, s.timer = ("fetch", 60) if s.food else ("idle", 3)

    def fire_job(s):
        s.job_fired, s.job_fire_t = True, s.job_t
        j = s.job
        try:
            msg = j["run"]()
            if j.get("undo"):
                s.push_undo(j.get("target", ""), j["undo"])
        except Exception as e:  # программа не нашлась, окно уже закрыто и т. п.
            msg = f"Не вышло: {e}"
        s.log(j.get("action", "?"), j.get("target", ""), msg)
        s.say(msg, 3, j.get("icon"))
        if j.get("icon") or j["anim"] == "dig":
            s.carry = (j.get("icon") or "box", s.clock + 1.2)
        s.mood_add(1)

    def job_step(s, dt, cx):
        j = s.job
        if s.job_phase == "go":
            if j["x"] is None or abs(j["x"] - cx) < 4:
                s.job_phase, s.job_t, s.job_fired = "act", 0.0, False
                if j["anim"] == "jump":
                    s.vy = -560.0
                return
            s.dir = 1 if j["x"] > cx else -1
            s.x += s.dir * min(RUN * dt, abs(j["x"] - cx))
            return
        s.job_t += dt
        if j["anim"] != "jump" and not s.job_fired and s.job_t >= 0.8:
            s.fire_job()
        if s.job_fired and s.job_t >= s.job_fire_t + 0.5 and s.y >= s.ground:
            s.next_job()
