# Python-Based Client-Server Chat Application Using TCP Sockets
**Subject:** Computer Networks (CNR) Laboratory  |  **Language:** Python 3 (standard library only)

---
## PART 1 — PROJECT OVERVIEW
**Title:** Python-Based Client-Server Chat Application Using TCP Sockets

**Problem Statement:** People on a network need a simple way to exchange text messages in real time. This project builds a multi-client chat system where one server accepts many TCP connections, receives each message, and delivers it to every connected client, while recording all activity in a log file.

**Objectives**
1. Implement the client-server architecture using Python TCP sockets.
2. Support many simultaneous clients using multithreading.
3. Demonstrate socket creation, bind, listen, accept, connect, send, recv, close.
4. Provide chat commands (`/users`, `/help`, `/time`, `/quit`) and server events.
5. Store every message/event with date and time in a persistent log.
6. Handle errors without crashing (disconnects, invalid input, duplicate names).

**Scope:** LAN / localhost text chat, one public room, plain-text protocol, no encryption/authentication (listed as future scope).

**Features:** multi-client broadcast; unique validated usernames; join/leave notices; online-user count; 4 chat commands; admin console on server (`/users`, `/shutdown`); persistent chat log; terminal client + Tkinter GUI client; graceful shutdown.

**Technologies:** Python 3, `socket`, `threading`, `datetime`, `re`, file handling, `tkinter` (GUI), `queue`.

---
## PROJECT STRUCTURE (purpose of every file)
```
Python_Chat_Application/
├── server/
│   ├── server.py        # The TCP server: socket/bind/listen/accept, one thread per client,
│   │                    #   commands, broadcasting, admin console, safe shutdown
│   └── chat_logger.py   # Thread-safe logger -> writes [date time] user: message to a file
├── client/
│   ├── client.py        # Terminal client + shared connect_to_server() helper
│   └── gui_client.py    # Tkinter GUI client (imports helper from client.py)
├── chat_logs/
│   └── chat_log.txt     # Created automatically; appended on every run (persistent)
├── docs/
│   └── CNR_Concepts_Viva_Report.md   # CN concepts mapped to code, 20+ viva Q&A, report text
├── screenshots/         # Put your own screenshots here for the report
├── requirements.txt     # No external packages needed
└── README.md            # This file
```

---
## PART 2 — SYSTEM DESIGN
### Client-Server Architecture
```
 +-----------+                                         +-----------+
 | Client 1  |--\                                   /--| Client 3  |
 | (Shruti)  |   \        TCP connections          /   | (Rahul)   |
 +-----------+    \    +---------------------+    /    +-----------+
                   +-->|       SERVER        |<--+
 +-----------+    /    |  IP:Port 0.0.0.0:5000|    \
 | Client 2  |---/     |  - listening socket  |     \
 | (Poonam)  |         |  - 1 thread/client   |
 +-----------+         |  - clients{} + lock  |
                       |  - ChatLogger        |
                       +----------+----------+
                                  |
                          chat_logs/chat_log.txt
```
Clients never talk to each other directly: **every message goes Client → Server → all Clients.**

### Data Flow Diagram
```
 [User types] -> Client send() --TCP--> Server thread recv()
        -> validate / is it a /command?
              |-- command -> build reply -> send to ONLY that client
              |-- chat    -> ChatLogger.log_message() -> file
                          -> broadcast(): send() to EVERY client -> Client recv thread -> screen
```

### Communication Flow
1. Server: `socket → bind → listen → accept (loop)`.
2. Client: `socket → connect` (TCP 3-way handshake SYN, SYN-ACK, ACK).
3. Client sends username line; server validates and replies `USERNAME_OK` / `USERNAME_ERROR`.
4. Server announces "X joined", sends updated user list.
5. Both sides now exchange lines at any time (full duplex).
6. `/quit` or socket close → server removes client, announces "X left".
7. Admin `/shutdown` → server notifies all, closes all sockets.

### Sequence Diagram
```
 Shruti(Client1)        Server                 Rahul(Client3)
     |--connect()-------->|                          |
     |--"Shruti\n"------->| validate + register      |
     |<--USERNAME_OK------|                          |
     |<--Server: Shruti joined----|                  |
     |                    |<-------connect()---------|
     |                    |<-------"Rahul\n"---------|
     |<--Server: Rahul joined-----|--USERNAME_OK---->|
     |--"Hello everyone!">|--log to file             |
     |<--Shruti: Hello everyone!--|--same message--->|
     |                    |<--"Hi Shruti!"-----------|
     |<--Rahul: Hi Shruti!|--same message----------->|
     |                    |<-------"/quit"-----------|
     |<--Server: Rahul left-------|--Goodbye!------->X
```
### How multiple clients communicate
The server's main thread only runs `accept()`. Each accepted connection gets its own thread (`handle_client`) that blocks on `readline()` for that client. When any thread receives a chat line, it calls `broadcast()`, which loops over the shared `clients` dictionary and `sendall()`s the line to every socket. A `Lock` protects the dictionary, and each client has its own send-lock so two threads never interleave bytes on one socket.

### Protocol (application layer)
Text lines ending in `\n` (UTF-8). TCP is a *byte stream* without message boundaries, so the newline is our message delimiter. Special server line `@@USERS@@ a,b,c` updates the GUI user list.

---
## PART 3 — SOURCE CODE
Complete, tested code is in the files above:
`server/server.py`, `server/chat_logger.py`, `client/client.py`, `client/gui_client.py`.
All imports match the folder structure (`server.py` imports `chat_logger` from its own folder; `gui_client.py` imports from `client.py` in its own folder), so **always run each file from inside its own folder**.

### Bugs I checked for (and how they are prevented)
| Potential bug | Prevention in code |
|---|---|
| Two threads change the client dictionary together | `clients_lock` around every access |
| Two threads write the same socket at once | per-client `_send_lock` |
| Server freezes when one client dies | one thread per client; `broadcast()` ignores `OSError` |
| Broadcast holds lock while sending (deadlock/slow) | copy list under lock, send outside it |
| Two users pick same name at the same time | duplicate check + insert inside one lock |
| Name spoofing (`server`, `SERVER`) | reserved-name check, case-insensitive duplicate check |
| Port stays busy after restart | `SO_REUSEADDR` |
| `accept()` blocks forever and Ctrl+C is ignored | `settimeout(1.0)` + loop re-checks `running` |
| TCP merges/splits messages | newline-delimited framing via `makefile().readline()` |
| Huge message | line length limit + 500-char cut |
| Log file corrupted by parallel writes | lock inside `ChatLogger` |
| GUI crash from updating widgets in a thread | receiver thread -> `queue` -> `root.after()` polling |

---
## PART 4 — SETUP INSTRUCTIONS
### 1. Install Python
Download Python 3.8+ from https://www.python.org/downloads/ . On Windows tick **"Add Python to PATH"**. Check: `python --version` (Linux/macOS: `python3 --version`). Tkinter comes with Windows/macOS Python; on Ubuntu run `sudo apt install python3-tk`.
### 2. Create the folders
Unzip the provided project, or create manually:
```
mkdir Python_Chat_Application
cd Python_Chat_Application
mkdir server client chat_logs screenshots docs
```
and save each file in its folder. (`chat_logs` is also auto-created.)
### 3. Run the server (Terminal 1)
```
cd Python_Chat_Application/server
python server.py                # default 0.0.0.0:5000
python server.py --port 6000    # custom port
```
### 4–6. Run Clients 1, 2, 3 (Terminals 2, 3, 4)
```
cd Python_Chat_Application/client
python client.py          # then enter: IP 127.0.0.1, port 5000, username
```
Or in one line: `python client.py 127.0.0.1 5000 Shruti` / `... Poonam` / `... Rahul`.
GUI version: `python gui_client.py`, fill username/IP/port, click **Connect**.
### 7. Test broadcasting
Type `Hello everyone!` in Shruti's window — it appears in all three windows. Reply from Rahul — appears everywhere. Try `/users`, `/time`, `/help`, `/foo`, `/quit`.
### 8. View chat logs
`chat_logs/chat_log.txt` — open in Notepad, or `type chat_logs\chat_log.txt` (Windows) / `cat chat_logs/chat_log.txt` (Linux/macOS). It keeps old entries after the server is closed.
### Same computer
Server and clients all use IP **127.0.0.1** (localhost), port 5000.
### Multiple computers on the same Wi-Fi/LAN
1. Connect all computers to the same Wi-Fi/router.
2. On the **server** computer find its IP: Windows `ipconfig` → "IPv4 Address" (e.g. `192.168.1.8`); Linux `hostname -I` or `ip a`; macOS `ipconfig getifaddr en0`.
3. Start server normally (it binds `0.0.0.0`, so it accepts LAN connections).
4. On other computers: `python client.py 192.168.1.8 5000 Poonam` — use the **server's** IP, never the client's own.
5. If it fails: allow Python through the firewall (Windows Defender Firewall → allow `python.exe` on Private networks) or allow inbound TCP port 5000; make sure all devices are on the same network (not a guest Wi-Fi with client isolation).

---
## PART 5 — TESTING
These were executed against the real code (3 simultaneous clients, localhost).
| # | Test Case | Input/Action | Expected Result | Status |
|---|---|---|---|---|
| 1 | Server startup | `python server.py` | Server starts listening | Pass |
| 2 | Client connection | Connect client | Client connects, welcome message | Pass |
| 3 | Multiple clients | Connect 3 clients | All remain connected | Pass |
| 4 | Message | Send message | Message delivered | Pass |
| 5 | Broadcast | Shruti sends message | Poonam and Rahul receive it | Pass |
| 6 | /users | Enter command | Active users displayed | Pass |
| 7 | /time | Enter command | Server time displayed | Pass |
| 8 | /help | Enter command | Command list displayed | Pass |
| 9 | Invalid command | `/foo` | "Invalid command" reply | Pass |
| 10 | /quit | Client exits | Disconnects safely, others notified | Pass |
| 11 | Chat log | Send messages | Entries stored in `chat_log.txt` | Pass |
| 12 | Duplicate username | Second "Shruti"/"shruti" | Rejected | Pass |
| 13 | Invalid username | `ab`, `bad name!`, `Server` | Rejected | Pass |
| 14 | Empty message | Press Enter only | Not sent / "Empty message ignored" | Pass |
| 15 | Server unavailable | Client to closed port | "Server unavailable" message | Pass |
| 16 | Invalid IP / port | `not.a.host`, port `99999` | Clear error, no crash | Pass |
| 17 | Abrupt disconnect | Client socket closed without /quit | "left the chat", server keeps running | Pass |
| 18 | Server shutdown | `/shutdown` on server | Clients notified and closed | Pass |

*(The Tkinter GUI could not be opened in my headless test environment; its logic reuses the tested `connect_to_server()` helper. Please run it once on your PC and take screenshots.)*

---
## PART 6 — OUTPUT DEMONSTRATION (real captured output)
**Server starting**
```
[08-10-2026 15:08:04] Server started. Listening on 0.0.0.0:5056
Admin commands: /users  /shutdown  /help
```
**Clients connecting / joining / multiple clients**
```
[08-10-2026 15:07:48] Connection from 127.0.0.1:54484
[08-10-2026 15:07:48] Shruti joined the chat.  (online: 1)
[08-10-2026 15:07:48] Poonam joined the chat.  (online: 2)
[08-10-2026 15:07:48] Rahul joined the chat.  (online: 3)
```
**Client side (Poonam's terminal)**
```
Server: Welcome Poonam! 2 user(s) online. Type /help for commands.
Server: Rahul joined the chat. Users online: 3
Shruti: Hello everyone!
Rahul: Hello Shruti!
> /users
Server: Online users (3): Poonam, Rahul, Shruti
> /time
Server: Current server time is 08-10-2026 15:07:51
> /foo
Server: Invalid command '/foo'. Type /help for the list.
> /quit
Server: Goodbye!
Disconnected.
```
**User leaving (Shruti's screen)**
```
Server: Poonam left the chat. Users online: 2
```
**Error examples**
```
[Error] Server unavailable (connection refused). Is the server running? Check IP/port.
[Rejected] Username already in use. Choose another one.
```
**Chat log**
```
[08-10-2026 15:07:47] Server started on 0.0.0.0:5055
[08-10-2026 15:07:48] Shruti joined the chat.
[08-10-2026 15:07:48] Poonam joined the chat.
[08-10-2026 15:07:48] Rahul joined the chat.
[08-10-2026 15:07:50] Shruti: Hello everyone!
[08-10-2026 15:07:50] Rahul: Hello Shruti!
[08-10-2026 15:07:53] Poonam left the chat.
[08-10-2026 15:07:54] Server shut down.
```
**GUI layout**
```
+--------------------------------------------------------------------+
| Username:[Shruti] Server IP:[127.0.0.1] Port:[5000] [Connect][Disconnect] |
+--------------------------------------------------+-----------------+
| Server: Welcome Shruti!...                       | Connected Users |
| Shruti: Hello everyone!                          |  Poonam         |
| Rahul: Hello Shruti!                             |  Rahul          |
|                                                  |  Shruti         |
+--------------------------------------------------+-----------------+
| [ Type a message...                         ]  [ Send ]            |
| Status: Connected to 127.0.0.1:5000 as Shruti                      |
+--------------------------------------------------------------------+
```
Parts 7 (Viva) and 8 (Report), plus concept-to-code mapping, are in `docs/CNR_Concepts_Viva_Report.md`.

---
## FINAL STEP-BY-STEP DEMO GUIDE
1. Open 4 terminals. 2. Terminal 1: `cd server && python server.py`. 3. Terminals 2–4: `cd client && python client.py 127.0.0.1 5000 Shruti` (then Poonam, Rahul). 4. Send messages from each; show they appear everywhere. 5. Run `/users`, `/time`, `/help`, an invalid command. 6. Try a duplicate name in a 5th window. 7. Close one client with `/quit`, another by closing the window — show the server keeps running. 8. Show the error handling: with the server stopped, start a client to display "Server unavailable". 9. Type `/shutdown` in the server window. 10. Open `chat_logs/chat_log.txt`. 11. Optional: run `gui_client.py` for the GUI demo and take screenshots.
