#!/usr/bin/env python3

import os
import socket
import time
import threading

import sounddevice as sd
import whisper
import numpy as np

# =========================
# 設定
# =========================

SOCK_PATH = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR", "/tmp"),
    "ibus-voiceinput.sock",
)
MODEL_NAME = "medium" # base / small / medium / large / large-v2 / v3

SAMPLE_RATE = 16000
CHANNELS = 1

MIN_RECORD_SECONDS = 0.5
MAX_RECORD_SECONDS = 30.0

# =========================
# 状態
# =========================

state = "IDLE"  # IDLE, RECORDING, TRANSCRIBING, RESULT_READY
state_lock = threading.Lock()

stream = None
audio_chunks = []
record_start_time = None

result_text = None

# =========================
# 録音コールバック
# =========================

def audio_callback(indata, frames, time_info, status):
    print("audio_callback: acquiring lock")
    with state_lock:
        print("audio_callback: lock acquired")
        if state != "RECORDING":
            print("audio_callback: releasing lock")
            return
        print("audio_callback: releasing lock")
    audio_chunks.append(indata.copy())

# =========================
# 内部ユーティリティ
# =========================

def _stop_stream():
    global stream
    if stream is not None:
        stream.stop()
        stream.close()
        stream = None

def _collect_audio():
    if not audio_chunks:
        return None
    return np.concatenate(audio_chunks, axis=0)[:, 0]

# =========================
# タイムアウト監視
# =========================

def record_timeout_watcher(start_time):
    global state
    time.sleep(MAX_RECORD_SECONDS)

    print("record_timeout_watcher: acquiring lock")
    with state_lock:
        print("record_timeout_watcher: lock acquired")
        if state != "RECORDING":
            print("record_timeout_watcher: releasing lock")
            return
        print("auto stop by timeout")
        state = "TRANSCRIBING"
        print("record_timeout_watcher: releasing lock")

    _stop_stream()
    threading.Thread(target=_transcribe_and_store, daemon=True).start()

# =========================
# 録音制御
# =========================

def start_recording():
    global state, stream, audio_chunks, record_start_time

    print("start_recording: acquiring lock")
    with state_lock:
        print("start_recording: lock acquired")
        if state != "IDLE":
            print(f"cannot start recording: state is {state}")
            print("start_recording: releasing lock")
            return False

        print("start recording")
        state = "RECORDING"
        audio_chunks = []
        record_start_time = time.time()
        print("start_recording: releasing lock")

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=audio_callback,
    )
    stream.start()

    threading.Thread(
        target=record_timeout_watcher,
        args=(record_start_time,),
        daemon=True,
    ).start()

    return True

def stop_recording():
    global state

    print("stop_recording: acquiring lock")
    with state_lock:
        print("stop_recording: lock acquired")
        if state != "RECORDING":
            print(f"cannot stop recording: state is {state}")
            print("stop_recording: releasing lock")
            return False
        print("manual stop")
        state = "TRANSCRIBING"
        print("stop_recording: releasing lock")

    _stop_stream()
    threading.Thread(target=_transcribe_and_store, daemon=True).start()
    return True

def abort_recording():
    global state, audio_chunks, record_start_time

    print("abort_recording: acquiring lock")
    with state_lock:
        print("abort_recording: lock acquired")
        if state != "RECORDING":
            print(f"cannot abort recording: state is {state}")
            print("abort_recording: releasing lock")
            return False
        print("abort")
        state = "IDLE"
        record_start_time = None
        print("abort_recording: releasing lock")

    _stop_stream()
    audio_chunks = []
    return True

# =========================
# 推論
# =========================

def _transcribe_and_store():
    global state, result_text, record_start_time

    audio = _collect_audio()

    duration = time.time() - record_start_time
    if audio is None or duration < MIN_RECORD_SECONDS:
        print("recording too short -> abort")
        print("_transcribe_and_store: acquiring lock")
        with state_lock:
            print("_transcribe_and_store: lock acquired")
            state = "IDLE"
            record_start_time = None
            print("_transcribe_and_store: releasing lock")
        return

    print("transcribing...")
    result = model.transcribe(
        audio,
        language="ja",
        fp16=False,
        temperature=0.0,
    )

    print("_transcribe_and_store: acquiring lock")
    with state_lock:
        print("_transcribe_and_store: lock acquired")
        result_text = result["text"].strip()
        state = "RESULT_READY"
        record_start_time = None
        print("_transcribe_and_store: releasing lock")

# =========================
# 結果取得
# =========================

def get_result():
    global state, result_text, record_start_time

    print("get_result: acquiring lock")
    with state_lock:
        print("get_result: lock acquired")
        if state != "RESULT_READY":
            print("get_result: releasing lock")
            return None

        text = result_text
        result_text = None
        state = "IDLE"
        record_start_time = None
        print("get_result: releasing lock")
        return text

# =========================
# 状態取得
# =========================

def get_status():
    print("get_status: acquiring lock")
    with state_lock:
        print("get_status: lock acquired")
        if state == "RECORDING" and record_start_time is not None:
            elapsed = time.time() - record_start_time
            print("get_status: releasing lock")
            return f"{state}:{elapsed:.1f}:{MAX_RECORD_SECONDS}"
        print("get_status: releasing lock")
        return state

# =========================
# メイン
# =========================

def main():
    global model

    if os.path.exists(SOCK_PATH):
        os.remove(SOCK_PATH)

    print("loading whisper model...")
    model = whisper.load_model(MODEL_NAME)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCK_PATH)
    server.listen(1)

    print(f"whisper daemon ready: {SOCK_PATH}")

    while True:
        conn, _ = server.accept()
        try:
            cmd = conn.recv(1024).decode().strip()
            print("cmd:", cmd)

            if cmd == "start":
                ok = start_recording()
                conn.sendall(b"ok" if ok else b"busy")

            elif cmd == "stop":
                ok = stop_recording()
                conn.sendall(b"ok" if ok else b"no-op")

            elif cmd == "abort":
                ok = abort_recording()
                conn.sendall(b"aborted" if ok else b"no-op")

            elif cmd == "get":
                text = get_result()
                if text is None:
                    conn.sendall(b"(none)")
                else:
                    conn.sendall(text.encode("utf-8"))

            elif cmd == "status":
                status = get_status()
                print(f"status: {status}")
                conn.sendall(status.encode("utf-8"))

            else:
                conn.sendall(b"unknown command")

        except Exception as e:
            conn.sendall(f"error: {e}".encode())

        finally:
            conn.close()

if __name__ == "__main__":
    main()
