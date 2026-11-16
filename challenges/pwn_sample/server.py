import socket
import os
import threading

FLAG = os.environ.get("FLAG", "CTF{sample_pwn_flag_default}")
PORT = 1337

def handle_client(conn, addr):
    try:
        conn.sendall(b"=== Welcome to CTFd-Compose TCP Challenge ===\n")
        conn.sendall(b"Type 'flag' to retrieve your personal dynamic flag:\n> ")
        data = conn.recv(1024).strip()
        if data == b"flag":
            conn.sendall(f"Here is your flag: {FLAG}\n".encode())
        else:
            conn.sendall(b"Unknown command. Goodbye!\n")
    except Exception:
        pass
    finally:
        conn.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", PORT))
    server.listen(10)
    print(f"Server listening on port {PORT}...")

    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()

if __name__ == "__main__":
    main()
