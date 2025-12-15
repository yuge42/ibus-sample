#!/usr/bin/env python3

import socket
import time

SOCK_PATH = "/tmp/whisper.sock"

def send(cmd):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(SOCK_PATH)
    sock.sendall(cmd.encode())
    data = sock.recv(4096)
    sock.close()
    return data.decode()

def main():
    print("start recording")
    send("start")

    input("Press ENTER to stop recording")

    print("stop recording")
    text = send("stop")

    print("➡ result:", text)

if __name__ == "__main__":
    main()
