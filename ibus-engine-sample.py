#!/usr/bin/env python3

import os
import socket
import logging
import time
import gi

gi.require_version("IBus", "1.0")
from gi.repository import IBus, GLib

# ==================================================
# 設定
# ==================================================

SOCK_PATH = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR", "/tmp"),
    "ibus-voice-input.sock",
)

# Ctrl + Space でトグル
TOGGLE_KEY = IBus.KEY_space
TOGGLE_MASK = IBus.ModifierType.CONTROL_MASK

# polling 間隔
POLL_INTERVAL_MS = 200

# whisperd 側と合わせる（重要）
MAX_RECORD_SECONDS = 30.0

# ==================================================
# ログ
# ==================================================

logging.basicConfig(
    filename="/tmp/ibus-sample.log",
    level=logging.DEBUG,
    format="%(asctime)s %(message)s",
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

# ==================================================
# IBus Engine
# ==================================================

class SampleEngine(IBus.Engine):
    """
    トグル式・timeout 対応・安定版 Whisper IBus Engine
    """

    def __init__(self):
        super().__init__()

        # IBus 側状態
        self.state = "IDLE"  # IDLE, RECORDING, WAITING_RESULT

        # auto-repeat / release 対策
        self.toggle_pressed = False

        # polling
        self.poll_id = None

        # 録音開始時刻（server timeout 同期用）
        self.record_start_time = None

        logging.debug("SampleEngine initialized")

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
        if keyval == IBus.KEY_Escape and self.state != "IDLE":
            self.abort()
            return True

        return False

    # ------------------------------------------------
    # トグル処理
    # ------------------------------------------------

    def handle_toggle(self):
        logging.debug(f"toggle (state={self.state})")

        if self.state == "IDLE":
            self.start_recording()

        elif self.state == "RECORDING":
            self.stop_recording()

        # WAITING_RESULT 中は無視
        else:
            logging.debug("toggle ignored (waiting result)")

    # ------------------------------------------------
    # Whisper 制御
    # ------------------------------------------------

    def start_recording(self):
        logging.debug("start_recording")
        whisper_cmd("start")

        self.state = "RECORDING"
        self.record_start_time = time.time()

        self.update_preedit("🎤 音声入力中…")

        # RECORDING 中も polling は動かす（timeout 判定用）
        self.start_polling()

    def stop_recording(self):
        logging.debug("stop_recording")
        whisper_cmd("stop")

        self.state = "WAITING_RESULT"
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
        now = time.time()

        # --- サーバー側 timeout を想定した自動遷移 ---
        if self.state == "RECORDING":
            if self.record_start_time is not None:
                if now - self.record_start_time >= MAX_RECORD_SECONDS:
                    logging.debug("assume server auto-stop")
                    self.state = "WAITING_RESULT"
                    self.update_preedit("🧠 認識中…")

        # --- 結果取得 ---
        if self.state == "WAITING_RESULT":
            result = whisper_cmd("get")

            if result and result not in ("(none)", "(aborted)"):
                logging.debug(f"commit: {result}")
                self.commit_text(
                    IBus.Text.new_from_string(result)
                )
                self.reset_state()
                return False  # polling 終了

        return True  # polling 継続

    # ------------------------------------------------
    # 状態リセット
    # ------------------------------------------------

    def reset_state(self):
        logging.debug("reset_state")

        self.state = "IDLE"
        self.toggle_pressed = False
        self.record_start_time = None

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
    factory.add_engine("sample", SampleEngine)

    bus.request_name("org.freedesktop.IBus.Sample", 0)

    logging.debug("IBus Sample Engine started")
    loop.run()

if __name__ == "__main__":
    main()
