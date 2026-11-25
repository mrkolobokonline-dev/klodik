"""Сценки основы A: двери (уходит в одну, выходит из другой в новой шапке), распорядок дня (кофе утром,
чай в обед, пижама вечером, чистит зубы ночью), сон, который будит мышь, и «в игре сидит в углу»."""
from .common import *  # noqa: F401,F403
from .sprites import sprite_window
from .looks import HAT_ART, FACE

DOOR_W, DOOR_H = 40, 70


class Door:
    """Пиксельная дверь у края экрана: открывается/закрывается по phase 0..1."""
    def __init__(s, pet, side):
        s.pet, s.side = pet, side
        s.w, s.c = sprite_window(pet.root, DOOR_W, DOOR_H)
        x = pet.L if side < 0 else pet.R - DOOR_W
        s.w.geometry(f"{DOOR_W}x{DOOR_H}+{int(x)}+{int(pet.B - DOOR_H)}")
        s.open = -1.0
        s.draw(0.0)

    def draw(s, open_):
        if abs(open_ - s.open) < 0.05:
            return
        s.open = open_
        c = s.c
        c.delete("all")
        c.create_rectangle(0, 0, DOOR_W, DOOR_H, fill="#5c3a1a", outline="")          # коробка
        c.create_rectangle(4, 4, DOOR_W - 4, DOOR_H, fill="#1b1b1b", outline="")       # проём
        wd = int((DOOR_W - 8) * (1 - open_))                                           # створка уезжает
        if wd > 1:
            x0 = 4 if s.side > 0 else DOOR_W - 4 - wd
            c.create_rectangle(x0, 4, x0 + wd, DOOR_H, fill="#a0522d", outline="")
            c.create_rectangle(x0 + wd // 2 - 1, 36, x0 + wd // 2 + 2, 39, fill="#e8b923", outline="")

    def destroy(s):
        s.w.destroy()


class PetScenes:
    def scenes_load(s):
        s.door = None
        s.door_plan = None
        s.scene_done = {}
        s.ptr_last = None

    # --- двери ---
    def door_trip(s, hat=None):
        """Дойти до края, уйти в дверь, переодеться за кадром, выйти из другой двери."""
        if s.busy or s.surface or s.door_plan:
            return s.say("Сейчас не могу — занят.", 2)
        side = -1 if s.x + W / 2 < (s.L + s.R) / 2 else 1
        choices = [h for h in HAT_ART if h not in ("glasses", "geek")] + list(FACE)
        s.door_plan = {"side": side, "hat": hat or random.choice([h for h in choices if h != s.hat]), "phase": "go", "t": 0.0}
        s.state, s.timer = "door", 9999
        s.dir = side

    def door_tick(s, dt):
        p = s.door_plan
        if not p:
            return
        p["t"] += dt
        edge = s.L if p["side"] < 0 else s.R - W
        ph = p["phase"]
        if ph == "go":                                    # идёт к краю
            if abs(s.x - edge) > 3:
                s.x += s.dir * min(RUN * 0.8 * dt, abs(edge - s.x))
            else:
                s.door = Door(s, p["side"])
                p.update(phase="open", t=0.0)
        elif ph == "open":
            s.door.draw(min(1, p["t"] / 0.5))
            if p["t"] > 0.6:
                p.update(phase="enter", t=0.0)
        elif ph == "enter":                               # уходит в проём
            s.x += p["side"] * 90 * dt
            if p["t"] > 1.0:
                s.root.withdraw()
                p.update(phase="close", t=0.0)
        elif ph == "close":
            s.door.draw(max(0, 1 - p["t"] / 0.5))
            if p["t"] > 0.6:
                s.door.destroy()
                s.hat = p["hat"]                          # переоделся за кадром
                s.hat_var.set(s.hat)
                p.update(phase="away", t=0.0, side=-p["side"])
        elif ph == "away" and p["t"] > 1.5:
            s.door = Door(s, p["side"])
            s.x = (s.L - W * 0.6) if p["side"] < 0 else (s.R - W * 0.4)
            p.update(phase="open2", t=0.0)
        elif ph == "open2":
            s.door.draw(min(1, p["t"] / 0.5))
            if p["t"] > 0.5:
                s.root.deiconify()
                s.dir = -p["side"]
                p.update(phase="exit", t=0.0)
        elif ph == "exit":                                # выходит в новой шапке
            s.x += s.dir * 90 * dt
            if p["t"] > 1.2:
                p.update(phase="close2", t=0.0)
        elif ph == "close2":
            s.door.draw(max(0, 1 - p["t"] / 0.5))
            if p["t"] > 0.6:
                s.door.destroy()
                s.door = s.door_plan = None
                s.state, s.timer, s.key = "idle", 3, None
                s.save()
                s.emote("pride", "light")
                s.say(random.choice(["Та-дам! Новый образ!", "Ну как я?", "Переоделся!"]), 2)

    # --- распорядок дня ---
    def daily_scene(s):
        """Раз в 10 с: если подходит время и ещё не было сегодня — маленькая сценка."""
        if s.state != "idle" or s.busy or s.quiet_now() or s.prefs.get("working") or s.prefs.get("anim") == "min":
            return
        h, today = time.localtime().tm_hour, time.strftime("%Y-%m-%d")
        scene = ("coffee" if 7 <= h < 10 else "tea" if 12 <= h < 14 else "brush" if h == 23 or h == 0 else None)
        if not scene or s.scene_done.get(scene) == today or random.random() > 0.15:
            return
        s.scene_done[scene] = today
        s.carry = (scene, s.clock + 6)
        if scene == "coffee":
            s.yawn_until = s.clock + 1.6
            s.say(random.choice(["Утренний кофе… ммм.", "Без кофе я не Клодик."]), 3)
        elif scene == "tea":
            s.state, s.timer = "eat", 4
            s.say(random.choice(["Обеденный чай — святое.", "Пуэр бы сейчас…"]), 3)
        else:
            s.say("Чищу зубы перед сном.", 3)

    # --- сон: будит движение мыши рядом ---
    def sleep_wake(s):
        try:
            px, py = s.root.winfo_pointerxy()
        except tk.TclError:
            return
        last, s.ptr_last = s.ptr_last, (px, py)
        if s.state != "sleep" or not last:
            return
        moved = abs(px - last[0]) + abs(py - last[1])
        near = abs(px - (s.x + W / 2)) < 350 and abs(py - (s.y + H / 2)) < 300
        if moved > 60 and near:
            s.state, s.timer = "idle", 3
            s.emote("tired", "light")
            s.say(random.choice(["Ммм… я не сплю!", "А? Кто тут?", "Уже утро?"]), 2)

    def scene_command(s, seg):
        if re.search(r"смени\s+(?:шапку|образ|костюм)|переоденься|сходи переоденься", seg):
            return lambda: s.door_trip()
        return None
