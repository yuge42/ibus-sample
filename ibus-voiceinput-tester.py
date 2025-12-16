#!/usr/bin/env python3

import os
import socket
import time

SOCK_PATH = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR", "/tmp"),
    "ibus-voiceinput.sock",
)

def send(cmd):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(SOCK_PATH)
    sock.sendall(cmd.encode())
    data = sock.recv(4096).decode()
    sock.close()
    return data

def main():
    print("1: start")
    print("2: stop (commit)")
    print("3: abort")
    print("4: get result")
    print("5: get status")
    print("q: quit")

    while True:
        choice = input("> ").strip()

        if choice == "1":
            print(send("start"))

        elif choice == "2":
            print(send("stop"))

        elif choice == "3":
            print(send("abort"))

        elif choice == "4":
            result = send("get")
            if result != "(none)":
                print("➡", result)
            else:
                print("(no result yet)")

        elif choice == "5":
            status = send("status")
            print("status:", status)

        elif choice.lower() == "q":
            break

        else:
            print("unknown")

        time.sleep(0.1)

if __name__ == "__main__":
    main()
