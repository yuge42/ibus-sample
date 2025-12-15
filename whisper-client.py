#!/usr/bin/env python3

import socket

SOCK_PATH = "/tmp/whisper.sock"

def send(cmd):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(SOCK_PATH)
    sock.sendall(cmd.encode())
    data = sock.recv(4096)
    sock.close()
    return data.decode()

def main():
    while True:
        print()
        print("1: start recording")
        print("2: stop (commit)")
        print("3: abort (cancel)")
        print("q: quit")

        choice = input("> ").strip()

        if choice == "1":
            print(send("start"))

        elif choice == "2":
            print("➡", send("stop"))

        elif choice == "3":
            print(send("abort"))

        elif choice.lower() == "q":
            print("bye")
            break

        else:
            print("unknown choice")

if __name__ == "__main__":
    main()
