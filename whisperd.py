#!/usr/bin/env python3

import os
import socket
import sounddevice as sd
import whisper
import numpy as np

SOCK_PATH = "/tmp/whisper.sock"
SAMPLE_RATE = 16000
MODEL_NAME = "base"

stream = None
recording = False
audio_chunks = []

def audio_callback(indata, frames, time, status):
    if recording:
        audio_chunks.append(indata.copy())

def start_recording():
    global stream, recording, audio_chunks

    audio_chunks = []
    recording = True

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        callback=audio_callback,
    )
    stream.start()

def stop_recording():
    global stream, recording

    recording = False

    if stream is not None:
        stream.stop()
        stream.close()
        stream = None

    audio = np.concatenate(audio_chunks, axis=0)[:, 0]
    return audio

def main():
    if os.path.exists(SOCK_PATH):
        os.remove(SOCK_PATH)

    print("loading model...")
    model = whisper.load_model(MODEL_NAME)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCK_PATH)
    server.listen(1)

    print("whisper daemon ready")

    while True:
        conn, _ = server.accept()
        cmd = conn.recv(1024).decode().strip()
        print("cmd:", cmd)

        if cmd == "start":
            start_recording()
            conn.sendall(b"ok")

        elif cmd == "stop":
            audio = stop_recording()

            if len(audio) == 0:
                conn.sendall(b"(no audio)")
                conn.close()
                continue

            print("🧠 transcribing...")
            result = model.transcribe(
                audio,
                language="ja",
                fp16=False,
                temperature=0.0,
            )
            text = result["text"].strip()
            conn.sendall(text.encode())

        else:
            conn.sendall(b"unknown command")

        conn.close()

if __name__ == "__main__":
    main()
