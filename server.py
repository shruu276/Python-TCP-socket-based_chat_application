"""
server.py
---------
Multi-client TCP chat server.

Run:   python server.py [--host 0.0.0.0] [--port 5000]

Protocol (plain text, one message per line, UTF-8, terminated by '\n'):
  client -> server : first line = username, then chat text or /commands
  server -> client : "USERNAME_OK" or "USERNAME_ERROR <reason>" (handshake),
                     then chat lines, and "@@USERS@@ a,b,c" user-list updates
"""
import argparse
import re
import socket
import threading
from datetime import datetime

from chat_logger import ChatLogger

DEFAULT_HOST = "0.0.0.0"      # 0.0.0.0 = listen on all network interfaces
DEFAULT_PORT = 5000
MAX_MSG_LEN = 500
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,15}$")
USERS_PREFIX = "@@USERS@@ "   # special line used by GUI to refresh the user list


def now():
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")


class ClientConnection:
    """Holds one connected client: its socket, address, username and a send-lock."""

    def __init__(self, conn, addr, username):
        self.conn = conn
        self.addr = addr
        self.username = username
        # Two threads may send to the same client at once -> serialise with a lock
        self._send_lock = threading.Lock()

    def send(self, text):
        data = (text + "\n").encode("utf-8")
        with self._send_lock:
            self.conn.sendall(data)          # sendall() keeps sending until all bytes are out

    def close(self):
        try:
            self.conn.shutdown(socket.SHUT_RDWR)   # tell the peer we are finished
        except OSError:
            pass
        try:
            self.conn.close()
        except OSError:
            pass


class ChatServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.logger = ChatLogger()
        self.clients = {}                     # username -> ClientConnection
        self.clients_lock = threading.Lock()  # protects self.clients
        self.running = threading.Event()
        self.server_socket = None

    # ------------------------------------------------------------------ start
    def start(self):
        # 1. Socket creation: AF_INET = IPv4 addresses, SOCK_STREAM = TCP (reliable byte stream)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow quick restart of the server on the same port
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            # 2. Binding: attach the socket to (IP address, port)
            self.server_socket.bind((self.host, self.port))
            # 3. Listening: become a passive socket; up to 10 pending connections queued
            self.server_socket.listen(10)
        except (OSError, OverflowError) as err:
            print(f"[ERROR] Cannot start server on {self.host}:{self.port} -> {err}")
            self.server_socket.close()
            return

        # accept() will wake up every second so we can notice a shutdown request
        self.server_socket.settimeout(1.0)
        self.running.set()
        self.logger.log_event(f"Server started on {self.host}:{self.port}")
        print(f"[{now()}] Server started. Listening on {self.host}:{self.port}")
        print("Admin commands: /users  /shutdown  /help")

        threading.Thread(target=self.admin_console, daemon=True).start()

        try:
            while self.running.is_set():
                try:
                    # 4. Accepting: blocks until a client connects. Returns a NEW socket
                    #    (conn) dedicated to that client plus the client's address.
                    conn, addr = self.server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break                     # server socket closed -> stop loop
                print(f"[{now()}] Connection from {addr[0]}:{addr[1]}")
                # 5. Multithreading: one thread per client so nobody blocks anybody
                threading.Thread(target=self.handle_client, args=(conn, addr),
                                 daemon=True).start()
        except KeyboardInterrupt:
            print("\n[INFO] Ctrl+C received.")
        finally:
            self.shutdown()

    # --------------------------------------------------------- client handling
    def validate_username(self, name):
        if not USERNAME_RE.match(name):
            return "Username must be 3-15 characters: letters, digits or underscore."
        if name.lower() == "server":
            return "Username 'Server' is reserved."
        return None

    def register(self, client):
        """Add client to the dictionary. Returns an error text, or None if OK."""
        with self.clients_lock:
            if any(u.lower() == client.username.lower() for u in self.clients):
                return "Username already in use. Choose another one."
            self.clients[client.username] = client
        return None

    def handle_client(self, conn, addr):
        client = None
        # makefile() lets us read the TCP byte stream line by line
        reader = conn.makefile("r", encoding="utf-8", errors="replace", newline="\n")
        try:
            conn.settimeout(30)               # client must send username within 30 s
            username = reader.readline(100).strip()
            error = self.validate_username(username)
            if error:
                conn.sendall(f"USERNAME_ERROR {error}\n".encode("utf-8"))
                return
            client = ClientConnection(conn, addr, username)
            error = self.register(client)
            if error:
                conn.sendall(f"USERNAME_ERROR {error}\n".encode("utf-8"))
                client = None
                return
            conn.settimeout(None)             # normal blocking mode from now on

            client.send("USERNAME_OK")
            client.send(f"Server: Welcome {username}! {self.count()} user(s) online. "
                        f"Type /help for commands.")
            self.announce(f"{username} joined the chat.")
            self.broadcast_userlist()

            # Main receive loop: recv data -> process -> broadcast
            while self.running.is_set():
                line = reader.readline(MAX_MSG_LEN * 4)
                if not line:                  # empty string = client closed the connection
                    break
                msg = line.strip()
                if not msg:
                    client.send("Server: Empty message ignored.")
                    continue
                if msg.startswith("/"):
                    if not self.handle_command(client, msg):
                        break                 # /quit
                    continue
                msg = msg[:MAX_MSG_LEN]
                self.logger.log_message(username, msg)
                print(f"[{now()}] {username}: {msg}")
                self.broadcast(f"{username}: {msg}")
        except (ConnectionError, OSError, ValueError):
            pass                              # abrupt disconnect / broken socket
        finally:
            self.remove_client(client, conn, reader)

    def remove_client(self, client, conn, reader):
        if client is not None:
            with self.clients_lock:
                self.clients.pop(client.username, None)
            if self.running.is_set():
                self.announce(f"{client.username} left the chat.")
                self.broadcast_userlist()
            client.close()
        else:
            try:
                conn.close()
            except OSError:
                pass
        try:
            reader.close()
        except OSError:
            pass

    # ---------------------------------------------------------------- commands
    def handle_command(self, client, text):
        """Returns False if the client should be disconnected."""
        cmd = text.split()[0].lower()
        if cmd == "/users":
            client.send(f"Server: Online users ({self.count()}): {', '.join(self.usernames())}")
        elif cmd == "/time":
            client.send(f"Server: Current server time is {now()}")
        elif cmd == "/help":
            client.send("Server: Commands -> /users (list users), /time (server time), "
                        "/help (this help), /quit (disconnect)")
        elif cmd == "/quit":
            client.send("Server: Goodbye!")
            return False
        else:
            client.send(f"Server: Invalid command '{cmd}'. Type /help for the list.")
        return True

    # ---------------------------------------------------------------- helpers
    def usernames(self):
        with self.clients_lock:
            return sorted(self.clients.keys())

    def count(self):
        with self.clients_lock:
            return len(self.clients)

    def broadcast(self, text):
        """Send one line to every connected client."""
        with self.clients_lock:
            targets = list(self.clients.values())   # copy, so we don't hold the lock while sending
        for c in targets:
            try:
                c.send(text)
            except OSError:
                pass   # that client's own thread will detect the failure and clean up

    def broadcast_userlist(self):
        self.broadcast(USERS_PREFIX + ",".join(self.usernames()))

    def announce(self, event):
        """Server event: log it, print it, and broadcast it as 'Server: ...'."""
        self.logger.log_event(event)
        print(f"[{now()}] {event}  (online: {self.count()})")
        self.broadcast(f"Server: {event} Users online: {self.count()}")

    # -------------------------------------------------------- admin / shutdown
    def admin_console(self):
        while self.running.is_set():
            try:
                cmd = input().strip().lower()
            except (EOFError, KeyboardInterrupt):
                return
            if cmd == "/users":
                print(f"Connected users ({self.count()}): {', '.join(self.usernames()) or 'none'}")
            elif cmd == "/shutdown":
                self.shutdown()
                return
            elif cmd == "/help":
                print("Admin commands: /users  /shutdown  /help")
            elif cmd:
                print("Unknown admin command. Type /help")

    def shutdown(self):
        if not self.running.is_set():
            return
        self.running.clear()
        print(f"[{now()}] Shutting down server...")
        self.logger.log_event("Server shut down.")
        with self.clients_lock:
            clients = list(self.clients.values())
        for c in clients:
            try:
                c.send("Server: Server is shutting down. Goodbye!")
            except OSError:
                pass
            c.close()
        try:
            self.server_socket.close()        # Closing the socket releases the port
        except OSError:
            pass
        print("Server stopped.")


def main():
    parser = argparse.ArgumentParser(description="TCP chat server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="IP to bind (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port (default 5000)")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        print("[ERROR] Port must be between 1 and 65535.")
        return
    ChatServer(args.host, args.port).start()


if __name__ == "__main__":
    main()
