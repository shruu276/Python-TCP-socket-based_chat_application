"""
client.py
---------
Terminal chat client.

Run:   python client.py                       (asks for IP, port, username)
       python client.py 192.168.1.5 5000 Shruti
"""
import argparse
import socket
import threading

USERS_PREFIX = "@@USERS@@ "


def connect_to_server(host, port, username, timeout=5):
    """Create a TCP socket, connect, and perform the username handshake.
    Returns (sock, reader). Raises OSError (network) or ValueError (username rejected)."""
    # Socket creation: AF_INET = IPv4, SOCK_STREAM = TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))                       # TCP 3-way handshake happens here
        sock.sendall((username + "\n").encode("utf-8"))  # first line = username
        reader = sock.makefile("r", encoding="utf-8", errors="replace", newline="\n")
        reply = reader.readline().strip()
        if reply != "USERNAME_OK":
            raise ValueError(reply.replace("USERNAME_ERROR ", "", 1) or "Rejected by server.")
        sock.settimeout(None)
        return sock, reader
    except Exception:
        sock.close()
        raise


def describe_error(err):
    if isinstance(err, ConnectionRefusedError):
        return "Server unavailable (connection refused). Is the server running? Check IP/port."
    if isinstance(err, socket.gaierror):
        return "Invalid IP address / hostname."
    if isinstance(err, socket.timeout):
        return "Connection timed out. Check the IP address and your network."
    return f"Network error: {err}"


def receive_loop(reader, stop, quitting):
    """Runs in a separate thread so receiving never blocks typing (full duplex)."""
    try:
        for line in reader:
            line = line.rstrip("\n")
            if line.startswith(USERS_PREFIX):
                continue                                 # user list is only used by the GUI
            print(f"\r{line}\n> ", end="", flush=True)
    except (OSError, ValueError):
        pass
    finally:
        if not quitting.is_set():
            print("\n[Connection closed by server. Press Enter to exit.]")
        stop.set()


def main():
    parser = argparse.ArgumentParser(description="TCP chat client")
    parser.add_argument("host", nargs="?")
    parser.add_argument("port", nargs="?", type=int)
    parser.add_argument("username", nargs="?")
    args = parser.parse_args()

    host = args.host or input("Server IP [127.0.0.1]: ").strip() or "127.0.0.1"
    port = args.port
    if port is None:
        raw = input("Port [5000]: ").strip() or "5000"
        if not raw.isdigit():
            print("Invalid port: must be a number.")
            return
        port = int(raw)
    if not 1 <= port <= 65535:
        print("Invalid port: must be between 1 and 65535.")
        return

    username = args.username
    while True:
        if not username:
            username = input("Username: ").strip()
        try:
            sock, reader = connect_to_server(host, port, username)
            break
        except ValueError as err:                        # username rejected -> ask again
            print(f"[Rejected] {err}")
            username = None
        except OSError as err:
            print(f"[Error] {describe_error(err)}")
            return

    stop, quitting = threading.Event(), threading.Event()
    receiver = threading.Thread(target=receive_loop, args=(reader, stop, quitting), daemon=True)
    receiver.start()

    try:
        while not stop.is_set():
            msg = input("> ").strip()
            if stop.is_set():
                break
            if not msg:
                print("Empty message not sent.")
                continue
            try:
                sock.sendall((msg + "\n").encode("utf-8"))
            except OSError:
                print("[Error] Connection lost.")
                break
            if msg.lower() == "/quit":
                quitting.set()
                receiver.join(timeout=2)
                break
    except (KeyboardInterrupt, EOFError):
        quitting.set()
        try:
            sock.sendall(b"/quit\n")
        except OSError:
            pass
    finally:
        for obj in (reader, sock):                       # safe socket closure
            try:
                obj.close()
            except OSError:
                pass
        print("Disconnected.")


if __name__ == "__main__":
    main()
