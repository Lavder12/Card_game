import json
import socket as _socket
import threading as _threading
import queue as _queue_mod
import sys
import os
import pygame
import random
from typing import Optional, List, Tuple
import src.state as state
from src.config import (
    T, NET_PORT, GM_NETWORK, BG, ACCENT, TEXT, TEXT_DIM, YELLOW, RED, OUT_OK,
    BTN, BTN_H, PANEL_BORD, HAND_OPENING_SIZE, HAND_TARGET_SIZE,
    STALEMATE_THRESHOLD, GM_TIMED, TIMER_OK, TIMER_WARN, TIMER_CRIT, UNDO_CLR, _BASE_W,
    add_history, FIREBASE_URL
)
from src.models import (
    Card, NumEntry, Caravan, PlayerState, BotPersonality, PERSONALITIES, DEFAULT_PERSONALITY,
    standard_card_list, load_deck_selection, save_deck_selection, build_deck_from_selection,
    ensure_min30_selection, draw_to_hand, move_card_to_discard, move_entry_to_discard,
    can_attach_picture, can_play_number_on_caravan, can_play_picture_on_target,
    apply_jack, apply_king, apply_queen, apply_joker, discard_hand_card, disband_caravan,
    play_number, play_picture, check_game_end, get_bot_delay_ms
)
from src.ui import (
    draw_ui_background, draw_panel, draw_panel_title_bar, draw_text_center,
    draw_button, draw_minimal_chip, draw_text, draw_board, ui_rects, caravan_slots,
    build_entry_hitboxes, get_idx_at, trigger_shake, wrap_text, lighten
)

import urllib.request
import urllib.error
import time
import uuid

class FirebaseFriends:
    @staticmethod
    def _req(method, path, data=None):
        try:
            import urllib.request
            url = f"{FIREBASE_URL.rstrip('/')}{path}"
            req = urllib.request.Request(url, method=method)
            if data is not None:
                req.data = json.dumps(data).encode()
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=3) as res:
                body = res.read().decode()
                return json.loads(body) if body != "null" else None
        except: return None

    @staticmethod
    def sync_profile(code: str, name: str, icon: str):
        import time, threading
        from src.state import app_settings, app_stats
        if not code: return
        data = {
            "name": name, 
            "icon": icon, 
            "last_online": int(time.time()),
            "wins": app_stats.wins if app_stats else 0,
            "losses": app_stats.losses if app_stats else 0,
            "draws": app_stats.draws if app_stats else 0,
            "caps": app_settings.caps if app_settings else 0,
            "friends": app_settings.friends if app_settings else []
        }
        threading.Thread(target=lambda: FirebaseFriends._req("PATCH", f"/users/{code}.json", data), daemon=True).start()

    @staticmethod
    def lookup_friend(code: str) -> Optional[dict]:
        if not code: return None
        return FirebaseFriends._req("GET", f"/users/{code}.json")

    @staticmethod
    def send_friend_request(my_code: str, target_code: str, my_name: str):
        import threading
        if not my_code or not target_code: return
        data = {my_code: my_name}
        threading.Thread(target=lambda: FirebaseFriends._req("PATCH", f"/users/{target_code}/requests.json", data), daemon=True).start()

    @staticmethod
    def get_pending_requests(my_code: str) -> dict:
        if not my_code: return {}
        res = FirebaseFriends._req("GET", f"/users/{my_code}/requests.json")
        return res if isinstance(res, dict) else {}

    @staticmethod
    def remove_friend_request(my_code: str, from_code: str):
        import threading
        if not my_code or not from_code: return
        data = {from_code: None}
        threading.Thread(target=lambda: FirebaseFriends._req("PATCH", f"/users/{my_code}/requests.json", data), daemon=True).start()

    @staticmethod
    def add_mutual_friend(my_code: str, friend_code: str):
        import threading
        if not my_code or not friend_code: return
        data = {my_code: True}
        threading.Thread(target=lambda: FirebaseFriends._req("PATCH", f"/users/{friend_code}/new_friends.json", data), daemon=True).start()

    @staticmethod
    def pop_new_friends(my_code: str) -> list:
        if not my_code: return []
        res = FirebaseFriends._req("GET", f"/users/{my_code}/new_friends.json")
        if isinstance(res, dict) and res:
            import threading
            # Clear new_friends by setting it to None
            threading.Thread(target=lambda: FirebaseFriends._req("PUT", f"/users/{my_code}/new_friends.json", None), daemon=True).start()
            return list(res.keys())
        return []

    @staticmethod
    def get_all_users() -> dict:
        res = FirebaseFriends._req("GET", "/users.json")
        return res if isinstance(res, dict) else {}

    @staticmethod
    def get_global_event() -> int:
        res = FirebaseFriends._req("GET", "/server_state/global_caps.json")
        try:
            return int(res) if res is not None else 0
        except:
            return 0

    @staticmethod
    def add_to_global_event(amount: int):
        if amount <= 0: return
        import threading
        def _add():
            current = FirebaseFriends.get_global_event()
            FirebaseFriends._req("PUT", "/server_state/global_caps.json", current + amount)
        threading.Thread(target=_add, daemon=True).start()

class NetworkManager:
    def __init__(self):
        self.role:      str                      = ""
        self.connected: bool                     = False
        self.error:     str                      = ""
        self._q:        _queue_mod.Queue         = _queue_mod.Queue()
        self.lobby_id:  str                      = ""
        self.player_id: str                      = ""
        self.last_msg_time: int                  = 0
        self._polling_thread: Optional[_threading.Thread] = None
        self._fb_url:   str                      = FIREBASE_URL.rstrip("/")

    def _fb_get(self, path: str) -> any:
        # Returns the decoded JSON if successful.
        # Returns "NETWORK_ERROR" if there was an exception.
        try:
            req = urllib.request.Request(f"{self._fb_url}{path}")
            with urllib.request.urlopen(req, timeout=3) as res:
                data = res.read().decode()
                return json.loads(data) if data != "null" else None
        except: return "NETWORK_ERROR"

    def _fb_patch(self, path: str, data: dict) -> bool:
        try:
            req = urllib.request.Request(f"{self._fb_url}{path}", data=json.dumps(data).encode(), method="PATCH")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=3) as res: return True
        except: return False

    def _fb_put(self, path: str, data: dict) -> bool:
        try:
            req = urllib.request.Request(f"{self._fb_url}{path}", data=json.dumps(data).encode(), method="PUT")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=3) as res: return True
        except: return False

    def find_match(self) -> bool:
        try:
            lobbies = self._fb_get('/lobbies.json')
            if lobbies != "NETWORK_ERROR" and lobbies and isinstance(lobbies, dict) and "error" not in lobbies:
                for lid, ldata in lobbies.items():
                    if isinstance(ldata, dict) and ldata.get("state") == "waiting" and not ldata.get("private"):
                        self.lobby_id = lid
                        self.role = "client"
                        self.player_id = "p2"
                        if self._fb_patch(f"/lobbies/{self.lobby_id}.json", {"state": "playing"}):
                            self.connected = True
                            self._start_polling()
                            return True
                
            self.lobby_id = str(uuid.uuid4())[:8]
            self.role = "host"
            self.player_id = "p1"
            lobby_data = {
                "state": "waiting",
                "private": False,
                "created_at": int(time.time()),
                "p1_msgs": {},
                "p2_msgs": {}
            }
            if self._fb_put(f"/lobbies/{self.lobby_id}.json", lobby_data):
                self.connected = True
                return True
            return False
        except Exception as e:
            self.error = str(e)
            return False

    def create_private_match(self) -> str:
        try:
            code = str(random.randint(1000, 9999))
            self.lobby_id = code
            self.role = "host"
            self.player_id = "p1"
            lobby_data = {
                "state": "waiting",
                "private": True,
                "created_at": int(time.time()),
                "p1_msgs": {},
                "p2_msgs": {}
            }
            if self._fb_put(f"/lobbies/{self.lobby_id}.json", lobby_data):
                self.connected = True
                return code
            return ""
        except Exception as e:
            self.error = str(e)
            return ""

    def join_private_match(self, code: str) -> bool:
        try:
            lobby = self._fb_get(f"/lobbies/{code}.json")
            if lobby != "NETWORK_ERROR" and lobby and lobby.get("state") == "waiting" and lobby.get("private"):
                self.lobby_id = code
                self.role = "client"
                self.player_id = "p2"
                if self._fb_patch(f"/lobbies/{self.lobby_id}.json", {"state": "playing"}):
                    self.connected = True
                    self._start_polling()
                    return True
            self.error = "Room not found or already playing"
            return False
        except Exception as e:
            self.error = str(e)
            return False

    def poll_accept(self) -> bool:
        if self._polling_thread and self._polling_thread.is_alive(): return True
        if not self.connected or self.role != "host": return False
        
        lobby = self._fb_get(f"/lobbies/{self.lobby_id}.json")
        if lobby != "NETWORK_ERROR" and lobby and lobby.get("state") == "playing":
            self._start_polling()
            return True
        return False

    def _start_polling(self):
        self._polling_thread = _threading.Thread(target=self._recv_loop, daemon=True)
        self._polling_thread.start()

    def _recv_loop(self):
        opp_id = "p2" if self.role == "host" else "p1"
        last_keys = set()
        while self.connected:
            try:
                msgs = self._fb_get(f"/lobbies/{self.lobby_id}/{opp_id}_msgs.json")
                if msgs != "NETWORK_ERROR" and isinstance(msgs, dict):
                    for k, msg in msgs.items():
                        if k not in last_keys:
                            self._q.put(msg)
                            last_keys.add(k)
                
                lobby = self._fb_get(f"/lobbies/{self.lobby_id}/state.json")
                if lobby != "NETWORK_ERROR" and lobby is None:
                    # Lobby was actually deleted, not a network timeout.
                    self.connected = False
            except: pass
            time.sleep(0.5)

    def send(self, msg: dict):
        if not self.connected: return
        msg_id = str(int(time.time() * 1000)) + str(uuid.uuid4())[:4]
        _threading.Thread(target=self._fb_patch, args=(f"/lobbies/{self.lobby_id}/{self.player_id}_msgs.json", {msg_id: msg}), daemon=True).start()

    def poll(self) -> Optional[dict]:
        try: return self._q.get_nowait()
        except _queue_mod.Empty: return None

    def close(self):
        self.connected = False
        if self.lobby_id and self.role == "host":
            _threading.Thread(target=self._fb_put, args=(f"/lobbies/{self.lobby_id}.json", None), daemon=True).start()

    @staticmethod
    def local_ip() -> str:
        return "Firebase"


# ── Serialisation helpers ────────────────────────────────────
def _sc(c: Card)      -> dict: return {"r": c.rank, "s": c.suit}
def _dc(d: dict)      -> Card: return Card(d["r"], d.get("s"))
def _sne(ne: NumEntry)-> dict: return {"c": _sc(ne.card), "p": [_sc(x) for x in ne.pics]}
def _dne(d: dict)     -> NumEntry: return NumEntry(card=_dc(d["c"]), pics=[_dc(x) for x in d.get("p", [])])
def _scav(cv: Caravan)-> dict: return {"n": [_sne(ne) for ne in cv.nums]}
def _dcav(d: dict)    -> Caravan: return Caravan(nums=[_dne(n) for n in d.get("n", [])])

def _sp(p: PlayerState) -> dict:
    return {
        "name": p.name,
        "cavs": [_scav(c) for c in p.caravans],
        "deck": [_sc(c) for c in p.deck],
        "disc": [_sc(c) for c in p.discard],
        "hand": [_sc(c) for c in p.hand]
    }

def _dp(d: dict) -> PlayerState:
    cavs_raw = d.get("cavs", [])
    if not isinstance(cavs_raw, list): cavs_raw = []
    cavs = []
    for i in range(3):
        if i < len(cavs_raw) and cavs_raw[i]:
            cavs.append(_dcav(cavs_raw[i]))
        else:
            cavs.append(Caravan())
            
    return PlayerState(
        name=d.get("name", "Player"),
        caravans=cavs,
        deck=[_dc(c) for c in d.get("deck", [])],
        discard=[_dc(c) for c in d.get("disc", [])],
        hand=[_dc(c) for c in d.get("hand", [])]
    )

def net_encode(p1: PlayerState, p2: PlayerState, phase: str, p1_to_move: bool, oht: int) -> dict:
    return {"t": "s", "p1": _sp(p1), "p2": _sp(p2), "ph": phase, "pm": p1_to_move, "oht": oht}

def net_decode(d: dict):
    return _dp(d["p1"]), _dp(d["p2"]), d["ph"], d["pm"], d.get("oht", 0)


# ── Lobby screen ─────────────────────────────────────────────
def network_lobby_screen() -> Optional["NetworkManager"]:
    TINY = state.TINY
    SMALL = state.SMALL
    FONT = state.FONT
    TITLE = state.TITLE
    nm = None
    mode = ""
    status = ""
    private_code_input = ""
    pygame.event.clear()

    def _status_color(msg: str):
        low = msg.lower()
        return RED if any(w in low for w in ("fail", "error", "refused", "timed")) else OUT_OK

    screen = state.screen
    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    FPS = 60
    clock = pygame.time.Clock()

    while True:
        clock.tick(FPS)
        now = pygame.time.get_ticks()
        pw, ph = min(760, WIDTH - 40), min(470, HEIGHT - 60)
        panel = pygame.Rect(WIDTH // 2 - pw // 2, HEIGHT // 2 - ph // 2, pw, ph)
        draw_ui_background()
        draw_panel(panel, glow=True)
        draw_panel_title_bar(panel, "Matchmaking")
        title = "Network Game" if state.language == "en" else "Сетевая игра"
        draw_text_center(title, pygame.Rect(panel.x, panel.y + 8, pw, 52), ACCENT, TITLE)
        draw_text_center("Global Matchmaking", pygame.Rect(panel.x, panel.y + 56, pw, 24), TEXT_DIM, SMALL)
        pos = pygame.mouse.get_pos()

        info = pygame.Rect(panel.x + 24, panel.y + 92, pw - 48, ph - 176)
        tint = pygame.Surface((info.w, info.h), pygame.SRCALPHA)
        tint.fill((12, 28, 20, 110))
        screen.blit(tint, info.topleft)
        pygame.draw.rect(screen, PANEL_BORD, info, 1, border_radius=12)

        if mode == "":
            r_find = pygame.Rect(info.centerx - 160, info.y + 30, 320, 50)
            draw_button("Find Random Match" if state.language == "en" else "Случайная игра", r_find, pos, BTN, BTN_H, SMALL)
            
            r_create_priv = pygame.Rect(info.centerx - 160, info.y + 100, 320, 50)
            draw_button("Create Private Game" if state.language == "en" else "Создать закрытую игру", r_create_priv, pos, (50, 70, 90), (70, 90, 110), SMALL)
            
            r_join_priv = pygame.Rect(info.centerx - 160, info.y + 170, 320, 50)
            draw_button("Join via Code" if state.language == "en" else "Присоединиться по коду", r_join_priv, pos, (90, 70, 50), (110, 90, 70), SMALL)
            
            r_back = pygame.Rect(panel.x + (pw - 210) // 2, panel.bottom - 56, 210, 42)
            draw_button(T("back"), r_back, pos, (100, 28, 28), lighten((100, 28, 28), 30), SMALL)

        elif mode == "searching":
            dots = "." * (1 + (now // 400) % 3)
            draw_text_center(("Connecting to server" if state.language == "en" else "Подключение к серверу") + dots,
                             pygame.Rect(info.x, info.y + 34, info.w, 36), YELLOW, FONT)

        elif mode == "host":
            dots = "." * (1 + (now // 400) % 3)
            draw_text_center(("Waiting for opponent" if state.language == "en" else "Ожидание соперника") + dots,
                             pygame.Rect(info.x, info.y + 34, info.w, 36), YELLOW, FONT)
            
            r_cancel = pygame.Rect(panel.x + (pw - 210) // 2, panel.bottom - 56, 210, 42)
            draw_button("Cancel" if state.language == "en" else "Отмена", r_cancel, pos, (100, 28, 28), lighten((100, 28, 28), 30), SMALL)
            
            if nm and nm.poll_accept():
                return nm

        elif mode == "host_private":
            draw_text_center("Room Code" if state.language == "en" else "Код комнаты",
                             pygame.Rect(info.x, info.y + 30, info.w, 30), TEXT_DIM, SMALL)
            code_str = getattr(nm, "lobby_id", "????")
            draw_text_center(code_str, pygame.Rect(info.x, info.y + 70, info.w, 60), ACCENT, TITLE)
            
            dots = "." * (1 + (now // 400) % 3)
            draw_text_center(("Waiting for friend" if state.language == "en" else "Ожидание друга") + dots,
                             pygame.Rect(info.x, info.y + 150, info.w, 30), YELLOW, SMALL)
            
            r_cancel = pygame.Rect(panel.x + (pw - 210) // 2, panel.bottom - 56, 210, 42)
            draw_button("Cancel" if state.language == "en" else "Отмена", r_cancel, pos, (100, 28, 28), lighten((100, 28, 28), 30), SMALL)
            
            if nm and nm.poll_accept():
                return nm
                
        elif mode == "join_private":
            draw_text_center("Enter 4-digit code:" if state.language == "en" else "Введите 4-значный код:",
                             pygame.Rect(info.x, info.y + 30, info.w, 30), TEXT_DIM, SMALL)
            
            disp = private_code_input + ("_" if (now // 500) % 2 == 0 else " ")
            draw_text_center(disp, pygame.Rect(info.x, info.y + 80, info.w, 50), ACCENT, TITLE)
            
            r_join = pygame.Rect(info.centerx - 120, info.y + 160, 240, 50)
            can_join = len(private_code_input) == 4
            if can_join:
                draw_button("Join" if state.language == "en" else "Войти", r_join, pos, BTN, BTN_H, SMALL)
            else:
                draw_button("Join" if state.language == "en" else "Войти", r_join, pos, (60, 60, 60), (60, 60, 60), SMALL)
                
            r_cancel = pygame.Rect(panel.x + (pw - 210) // 2, panel.bottom - 56, 210, 42)
            draw_button("Cancel" if state.language == "en" else "Отмена", r_cancel, pos, (100, 28, 28), lighten((100, 28, 28), 30), SMALL)

        if status:
            draw_text_center(status, pygame.Rect(panel.x + 20, panel.bottom - 92, pw - 40, 20), _status_color(status), TINY)
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if nm: nm.close()
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if nm: nm.close(); nm = None
                    if mode:
                        mode = ""
                        status = ""
                        continue
                    return None
                if mode == "join_private":
                    if e.key == pygame.K_BACKSPACE:
                        private_code_input = private_code_input[:-1]
                        status = ""
                    elif e.unicode.isdigit() and len(private_code_input) < 4:
                        private_code_input += e.unicode
                        status = ""
                    elif e.key == pygame.K_RETURN and len(private_code_input) == 4:
                        status = "Connecting..." if state.language == "en" else "Подключение..."
                        nm = NetworkManager()
                        if nm.join_private_match(private_code_input):
                            return nm
                        else:
                            status = ("Error: " if state.language == "en" else "Ошибка: ") + nm.error
                            nm = None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if mode == "":
                    r_find = pygame.Rect(info.centerx - 160, info.y + 30, 320, 50)
                    r_create_priv = pygame.Rect(info.centerx - 160, info.y + 100, 320, 50)
                    r_join_priv = pygame.Rect(info.centerx - 160, info.y + 170, 320, 50)
                    r_back = pygame.Rect(panel.x + (pw - 210) // 2, panel.bottom - 56, 210, 42)
                    
                    if r_find.collidepoint(e.pos):
                        mode = "searching"
                        nm = NetworkManager()
                        if nm.find_match():
                            if nm.role == "client":
                                return nm
                            else:
                                mode = "host"
                        else:
                            status = ("Error: " if state.language == "en" else "Ошибка: ") + nm.error
                            mode = ""
                            nm = None
                    elif r_create_priv.collidepoint(e.pos):
                        nm = NetworkManager()
                        code = nm.create_private_match()
                        if code:
                            mode = "host_private"
                        else:
                            status = ("Error: " if state.language == "en" else "Ошибка: ") + nm.error
                            nm = None
                    elif r_join_priv.collidepoint(e.pos):
                        mode = "join_private"
                        private_code_input = ""
                        status = ""
                    elif r_back.collidepoint(e.pos):
                        return None
                elif mode in ("host", "host_private", "join_private"):
                    r_c = pygame.Rect(panel.x + (pw - 210) // 2, panel.bottom - 56, 210, 42)
                    if r_c.collidepoint(e.pos):
                        if nm: nm.close(); nm = None
                        mode = ""
                        status = ""
                    elif mode == "join_private":
                        r_join = pygame.Rect(info.centerx - 120, info.y + 160, 240, 50)
                        if r_join.collidepoint(e.pos) and len(private_code_input) == 4:
                            status = "Connecting..." if state.language == "en" else "Подключение..."
                            nm = NetworkManager()
                            if nm.join_private_match(private_code_input):
                                return nm
                            else:
                                status = ("Error: " if state.language == "en" else "Ошибка: ") + nm.error
                                nm = None


def _draw_net_hud(is_host: bool, is_my_turn: bool):
    TINY = state.TINY
    SMALL = state.SMALL
    role_lbl = "🖥 HOST" if is_host else "🔌 CLIENT"
    turn_lbl = "▶ YOUR TURN" if is_my_turn else "⏳ Opponent's turn…"
    draw_text(role_lbl, 8, 8, (120, 180, 255), TINY)
    draw_text(turn_lbl, 8, 8 + TINY.get_height() + 4, ACCENT if is_my_turn else TEXT_DIM, SMALL)


# ── Network match loop ────────────────────────────────────────
def run_network_match(nm: "NetworkManager") -> str:
    TINY = state.TINY
    SMALL = state.SMALL
    FONT = state.FONT
    from src.screens import pause_menu, end_screen
    from src.config import add_history

    is_host = (nm.role == "host")
    sel_keys = load_deck_selection()
    if sel_keys: sel_keys = ensure_min30_selection(sel_keys)

    WIDTH = state.WIDTH
    HEIGHT = state.HEIGHT
    FPS = 60
    clock = pygame.time.Clock()

    if is_host:
        p1 = PlayerState(state.app_settings.player_name,
                         [Caravan() for _ in range(3)],
                         build_deck_from_selection(sel_keys), [], [])
        p2 = PlayerState("Opponent",
                         [Caravan() for _ in range(3)],
                         build_deck_from_selection(sel_keys), [], [])
        draw_to_hand(p1, HAND_OPENING_SIZE)
        draw_to_hand(p2, HAND_OPENING_SIZE)
        opening_ht = 0
        nm.send(net_encode(p1, p2, "OPENING", True, 0))
    else:
        p1 = p2 = None
        while p1 is None:
            clock.tick(FPS)
            state.screen.fill(BG)
            draw_text_center("Waiting for host to start…",
                             pygame.Rect(0, HEIGHT // 2 - 20, WIDTH, 40), YELLOW, FONT)
            pygame.display.flip()
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    nm.close()
                    if state.app_settings: state.app_settings.save()
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    nm.close()
                    return "menu"
            if not nm.connected: return "menu"
            msg = nm.poll()
            if msg and msg.get("t") == "s":
                p1, p2, phase0, pm0, oht0 = net_decode(msg)
                opening_ht = oht0
                break

    phase = "OPENING"
    p1_to_move = True
    if not is_host:
        phase = phase0
        p1_to_move = pm0
        opening_ht = oht0

    def me() -> PlayerState: return p1 if is_host else p2
    def opp() -> PlayerState: return p2 if is_host else p1
    def my_turn() -> bool: return p1_to_move if is_host else (not p1_to_move)

    def sync():
        nm.send(net_encode(p1, p2, phase, p1_to_move, opening_ht))

    def apply_incoming(msg: dict):
        nonlocal p1, p2, phase, p1_to_move, opening_ht
        np1, np2, nph, npm, noht = net_decode(msg)
        for attr in ("caravans", "deck", "discard", "hand"):
            setattr(p1, attr, getattr(np1, attr))
            setattr(p2, attr, getattr(np2, attr))
        phase = nph
        p1_to_move = npm
        opening_ht = noht

    start_ms = pygame.time.get_ticks()
    selected = -1
    msg_str = ""
    msg_until = 0
    hand_scroll = 0
    consecutive_discards = 0
    hitboxes_dirty = True
    cached_hit: Optional[dict] = None

    while True:
        clock.tick(FPS)
        now = pygame.time.get_ticks()

        if not nm.connected:
            if state.sounds: state.sounds.play("lose")
            end_screen("Connection lost!", now - start_ms, 0)
            return "menu"

        while True:
            net_msg = nm.poll()
            if net_msg is None: break
            if net_msg.get("t") == "s":
                apply_incoming(net_msg)
                hitboxes_dirty = True
            elif net_msg.get("t") == "chat":
                msg_str = f"Opp: {net_msg.get('text', '')}"
                msg_until = now + 2500

        if hitboxes_dirty:
            _, ba_, pa_, _ = ui_rects()
            cached_hit = {
                "bot": build_entry_hitboxes("bot", caravan_slots(ba_), opp().caravans),
                "player": build_entry_hitboxes("player", caravan_slots(pa_), me().caravans),
            }
            hitboxes_dirty = False

        ui = draw_board(
            player=me(), bot=opp(),
            selected_idx=selected, msg=msg_str, msg_until=msg_until,
            start_ms=start_ms, phase=phase, bot_diff="LAN",
            hand_scroll=hand_scroll, pending_bot=not my_turn(),
            undo_count=0, consecutive_discards=consecutive_discards,
            cached_hitboxes=cached_hit, game_mode=GM_NETWORK,
            turn_start_ms=start_ms, personality_key=DEFAULT_PERSONALITY,
        )
        hand_scroll = ui.hand_scroll
        _draw_net_hud(is_host, my_turn())
        pygame.display.flip()

        if phase == "MAIN":
            ended, win, _ = check_game_end(me(), opp())
            if ended:
                elapsed = now - start_ms
                result = "win" if win == "player" else "loss"
                if state.app_stats:
                    state.app_stats.record(result, elapsed)
                    state.app_stats.save()
                if state.sounds: state.sounds.play("win" if result == "win" else "lose")
                add_history(result, "LAN", GM_NETWORK, elapsed, 0)
                if result == "win" and state.particles: state.particles.confetti(70)
                end_screen(T("player_wins") if result == "win" else T("bot_wins"), elapsed, 0)
                nm.close()
                return "menu"
            if consecutive_discards >= STALEMATE_THRESHOLD:
                elapsed = now - start_ms
                if state.app_stats:
                    state.app_stats.record("draw", elapsed)
                    state.app_stats.save()
                add_history("draw", "LAN", GM_NETWORK, elapsed, 0)
                end_screen(T("draw_stalemate"), elapsed, 0)
                nm.close()
                return "menu"

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                nm.close()
                if state.app_settings: state.app_settings.save()
                pygame.quit()
                sys.exit()

            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                r2 = pause_menu()
                if r2 == "quit_match":
                    nm.close()
                    return "menu"
                hitboxes_dirty = True
                continue

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if ui.pause_btn.collidepoint(*e.pos):
                    r2 = pause_menu()
                    if r2 == "quit_match":
                        nm.close()
                        return "menu"
                    hitboxes_dirty = True
                    continue

            if not my_turn(): continue

            if e.type == pygame.MOUSEWHEEL and ui.hand_scroll_on:
                hand_scroll = max(0, min(ui.hand_max_scroll, hand_scroll - e.y * 50))

            if e.type == pygame.KEYDOWN:
                n = len(me().hand)
                if e.key == pygame.K_RIGHT and n > 0:
                    selected = (max(selected, 0) + 1) % n
                elif e.key == pygame.K_LEFT and n > 0:
                    selected = (max(selected, 0) - 1) % n

                if e.key == pygame.K_d and phase == "MAIN" and 0 <= selected < len(me().hand):
                    if state.sounds: state.sounds.play("discard")
                    if discard_hand_card(me(), selected):
                        draw_to_hand(me(), HAND_TARGET_SIZE)
                        consecutive_discards += 1
                        hitboxes_dirty = True
                        p1_to_move = not p1_to_move
                        sync()
                        selected = -1

                cav_keys = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}
                if e.key in cav_keys and phase == "MAIN" and 0 <= selected < len(me().hand):
                    ci = cav_keys[e.key]
                    c = me().hand[selected]
                    if c.is_number():
                        ok, emsg = play_number(me(), selected, ci)
                        selected = -1
                        if not ok:
                            msg_str = emsg
                            msg_until = now + 1400
                        else:
                            if state.sounds: state.sounds.play("play_card")
                            consecutive_discards = 0
                            hitboxes_dirty = True
                            draw_to_hand(me(), HAND_TARGET_SIZE)
                            p1_to_move = not p1_to_move
                            sync()

            if phase == "OPENING" and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mpos = e.pos
                hi = get_idx_at(mpos, ui.hand_rects)
                if hi != -1:
                    selected = -1 if selected == hi else hi
                    continue
                if 0 <= selected < len(me().hand):
                    c = me().hand[selected]
                    if not c.is_number():
                        msg_str = T("opening_nums_only")
                        msg_until = now + 1200
                        selected = -1
                        continue
                    for ci, r in enumerate(ui.ply_slots):
                        if r.collidepoint(*mpos):
                            if not me().caravans[ci].empty():
                                msg_str = T("caravan_started")
                                msg_until = now + 1200
                                selected = -1
                                break
                            if state.sounds: state.sounds.play("deal")
                            card = me().hand.pop(selected)
                            me().caravans[ci].nums.append(NumEntry(card=card))
                            selected = -1
                            hitboxes_dirty = True
                            opening_ht += 1
                            p1_to_move = not p1_to_move
                            if opening_ht >= 6:
                                me().hand = me().hand[:HAND_TARGET_SIZE]
                                opp().hand = opp().hand[:HAND_TARGET_SIZE]
                                draw_to_hand(me(), HAND_TARGET_SIZE)
                                phase = "MAIN"
                                p1_to_move = True
                            sync()
                            break
                continue

            if phase == "MAIN" and e.type == pygame.MOUSEBUTTONDOWN:
                mpos = e.pos

                if e.button == 3:
                    hi = get_idx_at(mpos, ui.hand_rects)
                    if hi != -1:
                        if state.sounds: state.sounds.play("discard")
                        if discard_hand_card(me(), hi):
                            draw_to_hand(me(), HAND_TARGET_SIZE)
                            consecutive_discards += 1
                            hitboxes_dirty = True
                            p1_to_move = not p1_to_move
                            sync()
                        continue
                    for ci, r in enumerate(ui.ply_slots):
                        if r.collidepoint(*mpos):
                            if disband_caravan(me(), ci):
                                draw_to_hand(me(), HAND_TARGET_SIZE)
                                consecutive_discards += 1
                                hitboxes_dirty = True
                                p1_to_move = not p1_to_move
                                sync()
                            else:
                                msg_str = T("nothing_disband")
                                msg_until = now + 1000
                            break
                    continue

                if e.button == 1:
                    hi = get_idx_at(mpos, ui.hand_rects)
                    if hi != -1:
                        selected = -1 if selected == hi else hi
                        continue
                    if not (0 <= selected < len(me().hand)): continue
                    c = me().hand[selected]

                    if c.is_number():
                        for ci, r in enumerate(ui.ply_slots):
                            if r.collidepoint(*mpos):
                                ok, emsg = play_number(me(), selected, ci)
                                selected = -1
                                if not ok:
                                    msg_str = emsg
                                    msg_until = now + 1400
                                    break
                                if state.sounds: state.sounds.play("play_card")
                                consecutive_discards = 0
                                hitboxes_dirty = True
                                draw_to_hand(me(), HAND_TARGET_SIZE)
                                p1_to_move = not p1_to_move
                                sync()
                                break

                    elif c.is_picture():
                        hit = None
                        for r, own, ci, ei in ui.ply_boxes + ui.bot_boxes:
                            if r.collidepoint(*mpos):
                                hit = (own, ci, ei)
                                break
                        if not hit:
                            msg_str = T("face_needs_target")
                            msg_until = now + 1200
                            selected = -1
                            continue
                        own, ci, ei = hit
                        tgt = me() if own == "player" else opp()
                        ok, emsg = play_picture(me(), opp(), selected, tgt, ci, ei)
                        selected = -1
                        if not ok:
                            msg_str = emsg
                            msg_until = now + 1500
                            continue
                        pic = me().discard[-1] if me().discard else None
                        if pic and state.sounds:
                            if pic.rank == "J": state.sounds.play("jack")
                            elif pic.rank == "JKR":
                                state.sounds.play("joker")
                                trigger_shake(10, 400)
                            elif pic.rank == "K": state.sounds.play("king")
                            else: state.sounds.play("play_card")
                        consecutive_discards = 0
                        hitboxes_dirty = True
                        draw_to_hand(me(), HAND_TARGET_SIZE)
                        p1_to_move = not p1_to_move
                        sync()

    nm.close()
    return "menu"
