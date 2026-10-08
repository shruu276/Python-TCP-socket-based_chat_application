"""
gui_client.py
-------------
Tkinter GUI chat client. Run:  python gui_client.py
Uses the same protocol as client.py. A background thread receives data and puts it
in a Queue; the Tkinter main loop reads the queue (Tkinter is not thread-safe).
"""
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from client import connect_to_server, describe_error, USERS_PREFIX


class ChatGUI:
    def __init__(self, root):
        self.root = root
        root.title("CNR Chat Application - TCP Client")
        root.geometry("760x520")
        self.sock = None
        self.reader = None
        self.connected = False
        self.inbox = queue.Queue()

        # ---- top: connection settings
        top = tk.Frame(root, padx=8, pady=6)
        top.pack(fill="x")
        tk.Label(top, text="Username:").grid(row=0, column=0)
        self.e_user = tk.Entry(top, width=14)
        self.e_user.grid(row=0, column=1, padx=4)
        tk.Label(top, text="Server IP:").grid(row=0, column=2)
        self.e_ip = tk.Entry(top, width=15)
        self.e_ip.insert(0, "127.0.0.1")
        self.e_ip.grid(row=0, column=3, padx=4)
        tk.Label(top, text="Port:").grid(row=0, column=4)
        self.e_port = tk.Entry(top, width=7)
        self.e_port.insert(0, "5000")
        self.e_port.grid(row=0, column=5, padx=4)
        self.b_connect = tk.Button(top, text="Connect", width=10, command=self.connect)
        self.b_connect.grid(row=0, column=6, padx=4)
        self.b_disc = tk.Button(top, text="Disconnect", width=10, state="disabled",
                                command=self.disconnect)
        self.b_disc.grid(row=0, column=7)

        # ---- middle: chat area + users list
        mid = tk.Frame(root, padx=8)
        mid.pack(fill="both", expand=True)
        self.chat = scrolledtext.ScrolledText(mid, state="disabled", wrap="word")
        self.chat.pack(side="left", fill="both", expand=True)
        right = tk.Frame(mid, padx=6)
        right.pack(side="right", fill="y")
        tk.Label(right, text="Connected Users", font=("Arial", 10, "bold")).pack()
        self.users = tk.Listbox(right, width=20)
        self.users.pack(fill="y", expand=True)

        # ---- bottom: message box + status
        bottom = tk.Frame(root, padx=8, pady=6)
        bottom.pack(fill="x")
        self.e_msg = tk.Entry(bottom)
        self.e_msg.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.e_msg.bind("<Return>", lambda e: self.send())
        self.b_send = tk.Button(bottom, text="Send", width=10, state="disabled",
                                command=self.send)
        self.b_send.pack(side="right")
        self.status = tk.Label(root, text="Status: Disconnected", fg="red", anchor="w", padx=8)
        self.status.pack(fill="x")

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.poll_queue)

    # ---------------------------------------------------------------- actions
    def connect(self):
        username = self.e_user.get().strip()
        host = self.e_ip.get().strip()
        port_txt = self.e_port.get().strip()
        if not username or not host:
            messagebox.showwarning("Missing data", "Enter username and server IP.")
            return
        if not port_txt.isdigit() or not 1 <= int(port_txt) <= 65535:
            messagebox.showerror("Invalid port", "Port must be a number from 1 to 65535.")
            return
        self.status.config(text="Status: Connecting...", fg="orange")
        self.root.update_idletasks()
        try:
            self.sock, self.reader = connect_to_server(host, int(port_txt), username)
        except ValueError as err:
            self.status.config(text="Status: Disconnected", fg="red")
            messagebox.showerror("Username rejected", str(err))
            return
        except OSError as err:
            self.status.config(text="Status: Disconnected", fg="red")
            messagebox.showerror("Connection failed", describe_error(err))
            return
        self.connected = True
        self.status.config(text=f"Status: Connected to {host}:{port_txt} as {username}", fg="green")
        self.b_connect.config(state="disabled")
        self.b_disc.config(state="normal")
        self.b_send.config(state="normal")
        threading.Thread(target=self.receive_loop, daemon=True).start()

    def receive_loop(self):
        try:
            for line in self.reader:
                self.inbox.put(line.rstrip("\n"))
        except (OSError, ValueError):
            pass
        self.inbox.put(None)                 # None = connection closed

    def send(self):
        msg = self.e_msg.get().strip()
        if not self.connected:
            return
        if not msg:
            return                           # empty messages are not sent
        try:
            self.sock.sendall((msg + "\n").encode("utf-8"))
        except OSError:
            self.handle_closed("Connection lost.")
            return
        self.e_msg.delete(0, "end")
        if msg.lower() == "/quit":
            self.handle_closed("Disconnected.")

    def disconnect(self):
        if self.connected:
            try:
                self.sock.sendall(b"/quit\n")
            except OSError:
                pass
        self.handle_closed("Disconnected.")

    def handle_closed(self, text):
        was_connected = self.connected
        self.connected = False
        for obj in (self.reader, self.sock):
            try:
                obj.close()
            except (OSError, AttributeError):
                pass
        self.status.config(text="Status: Disconnected", fg="red")
        self.b_connect.config(state="normal")
        self.b_disc.config(state="disabled")
        self.b_send.config(state="disabled")
        self.users.delete(0, "end")
        if was_connected:
            self.show(f"[{text}]")

    # ---------------------------------------------------------------- display
    def show(self, text):
        self.chat.config(state="normal")
        self.chat.insert("end", text + "\n")
        self.chat.see("end")
        self.chat.config(state="disabled")

    def poll_queue(self):
        try:
            while True:
                line = self.inbox.get_nowait()
                if line is None:
                    if self.connected:
                        self.handle_closed("Connection closed by server.")
                elif line.startswith(USERS_PREFIX):
                    self.users.delete(0, "end")
                    for name in line[len(USERS_PREFIX):].split(","):
                        if name:
                            self.users.insert("end", name)
                else:
                    self.show(line)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)

    def on_close(self):
        if self.connected:
            self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    ChatGUI(window)
    window.mainloop()
