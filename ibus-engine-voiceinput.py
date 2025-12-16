#!/usr/bin/env python3

import os
import socket
import logging
import gi

gi.require_version("IBus", "1.0")
from gi.repository import IBus, GLib

# ==================================================
# 設定
# ==================================================

SOCK_PATH = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR", "/tmp"),
    "ibus-voiceinput.sock",
)

# Ctrl + Space でトグル
TOGGLE_KEY = IBus.KEY_space
TOGGLE_MASK = IBus.ModifierType.CONTROL_MASK

# polling 間隔
POLL_INTERVAL_MS = 200

# ==================================================
# ログ
# ==================================================

LOG_PATH = os.path.join(
    os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")),
    "ibus-voiceinput",
    "daemon.log"
)

# ==================================================
# Whisper socket client
# ==================================================

def whisper_cmd(cmd: str):
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCK_PATH)
        sock.sendall(cmd.encode("utf-8"))
        data = sock.recv(4096).decode("utf-8")
        sock.close()
        logging.debug(f"whisper_cmd {cmd} -> {data}")
        return data
    except Exception as e:
        logging.error(f"whisper_cmd error ({cmd}): {e}")
        return None

def get_server_state():
    """Get current state from the server"""
    return whisper_cmd("status")

# ==================================================
# IBus Engine
# ==================================================

class VoiceinputEngine(IBus.Engine):
    """
    トグル式・timeout 対応・安定版 Whisper IBus Engine
    Server state is the single source of truth.
    """

    def __init__(self):
        super().__init__()

        # auto-repeat / release 対策
        self.toggle_pressed = False

        # polling
        self.poll_id = None

        logging.debug("VoiceinputEngine initialized")

    # ------------------------------------------------
    # キーイベント
    # ------------------------------------------------

    def do_process_key_event(self, keyval, keycode, state):
        # key release は無視（auto-repeat 防止）
        if state & IBus.ModifierType.RELEASE_MASK:
            if keyval == TOGGLE_KEY:
                self.toggle_pressed = False
            return False

        ctrl = bool(state & TOGGLE_MASK)

        # Ctrl+Space トグル
        if keyval == TOGGLE_KEY and ctrl:
            if self.toggle_pressed:
                return True
            self.toggle_pressed = True
            self.handle_toggle()
            return True

        # Esc = abort
        if keyval == IBus.KEY_Escape:
            server_state = get_server_state()
            if server_state and server_state != "IDLE":
                self.abort()
                return True

        return False

    # ------------------------------------------------
    # トグル処理
    # ------------------------------------------------

    def handle_toggle(self):
        server_state = get_server_state()
        logging.debug(f"toggle (server_state={server_state})")

        if not server_state:
            logging.error("failed to get server state")
            return

        if server_state == "IDLE":
            self.start_recording()

        elif server_state == "RECORDING":
            self.stop_recording()

        # TRANSCRIBING or RESULT_READY 中は無視
        else:
            logging.debug(f"toggle ignored (server in {server_state})")

    # ------------------------------------------------
    # Whisper 制御
    # ------------------------------------------------

    def start_recording(self):
        logging.debug("start_recording")
        whisper_cmd("start")

        self.update_preedit("🎤 音声入力中…")

        # polling を開始して状態を監視
        self.start_polling()

    def stop_recording(self):
        logging.debug("stop_recording")
        whisper_cmd("stop")

        self.update_preedit("🧠 認識中…")

    def abort(self):
        logging.debug("abort")
        whisper_cmd("abort")
        self.reset_state()

    # ------------------------------------------------
    # polling
    # ------------------------------------------------

    def start_polling(self):
        if self.poll_id is None:
            self.poll_id = GLib.timeout_add(
                POLL_INTERVAL_MS,
                self.poll_result,
            )

    def stop_polling(self):
        if self.poll_id is not None:
            GLib.source_remove(self.poll_id)
            self.poll_id = None

    def poll_result(self):
        # サーバー状態を取得
        server_state = get_server_state()
        
        if not server_state:
            logging.error("failed to get server state during polling")
            return True  # polling 継続

        logging.debug(f"poll: server_state={server_state}")

        # サーバーが RECORDING から TRANSCRIBING に遷移したら preedit を更新
        if server_state == "TRANSCRIBING":
            self.update_preedit("🧠 認識中…")

        # 結果が準備できたら取得してコミット
        if server_state == "RESULT_READY":
            result = whisper_cmd("get")

            if result and result not in ("(none)", "(aborted)"):
                logging.debug(f"commit: {result}")
                self.commit_text(
                    IBus.Text.new_from_string(result)
                )
                self.reset_state()
                return False  # polling 終了

        # サーバーが IDLE に戻った場合（abort などで）
        if server_state == "IDLE":
            self.reset_state()
            return False  # polling 終了

        return True  # polling 継続

    # ------------------------------------------------
    # 状態リセット
    # ------------------------------------------------

    def reset_state(self):
        logging.debug("reset_state")

        self.toggle_pressed = False

        self.stop_polling()
        self.clear_preedit()

    # ------------------------------------------------
    # preedit
    # ------------------------------------------------

    def update_preedit(self, text: str):
        self.update_preedit_text(
            IBus.Text.new_from_string(text),
            len(text),
            True,
        )

    def clear_preedit(self):
        self.update_preedit_text(
            IBus.Text.new_from_string(""),
            0,
            False,
        )

# ==================================================
# main
# ==================================================

def main():
    IBus.init()
    loop = GLib.MainLoop()

    bus = IBus.Bus()
    factory = IBus.Factory.new(bus.get_connection())
    factory.add_engine("voiceinput", VoiceinputEngine)

    bus.request_name("org.freedesktop.IBus.Voiceinput", 0)

    logging.debug("IBus Voiceinput Engine started")
    loop.run()

if __name__ == "__main__":
    main()
