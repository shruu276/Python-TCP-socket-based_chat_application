# CNR Project — Concepts, Viva Questions and Report Content

## A. Why `AF_INET` and `SOCK_STREAM`
`socket.socket(socket.AF_INET, socket.SOCK_STREAM)`
- **AF_INET** = *Address Family, Internet*: the socket uses IPv4 addresses `(ip, port)`.
- **SOCK_STREAM** = a connection-oriented, reliable, ordered byte stream, which means **TCP**. (`SOCK_DGRAM` would be UDP.)

## B. Concepts mapped to the code
| Concept | Where in the code |
|---|---|
| Client-Server Architecture | `server.py` waits and serves; `client.py`/`gui_client.py` initiate. Clients talk only to the server. |
| TCP/IP | `SOCK_STREAM` (TCP) over `AF_INET` (IP) in both programs. |
| Socket programming | `socket()`, `bind()`, `listen()`, `accept()`, `connect()`, `sendall()`, `readline()`/`recv`, `close()`. |
| Port numbers | `DEFAULT_PORT = 5000` — identifies the chat process on the server machine. Also each client gets an ephemeral port (shown as `127.0.0.1:54484` in the server output). |
| IP addresses | Server binds `0.0.0.0` (all interfaces); clients connect to `127.0.0.1` or the server's LAN IP. |
| Connection-oriented communication | `connect()` ↔ `accept()` establish a TCP connection (3-way handshake) *before* data flows; `close()` ends it. |
| Reliable transmission | TCP gives acknowledgements, retransmission, ordering — so chat lines arrive complete and in order without extra code. `sendall()` guarantees all bytes are handed to TCP. |
| Full-duplex | `client.py` runs a receiver thread while the main thread sends; each side can send and receive at the same time. |
| Multithreading | `threading.Thread(target=self.handle_client, ...)` per client; `clients_lock` for shared data. |
| Broadcasting | `ChatServer.broadcast()` loops over `clients` and sends to each socket (application-level broadcast; TCP itself is unicast). |
| Application layer | Our own text protocol: username line, `/commands`, `USERNAME_OK`, `@@USERS@@`, newline-delimited messages — running on top of TCP like HTTP/SMTP do. |

---
## PART 7 — VIVA QUESTIONS (26)
1. **What is a socket?** An endpoint of two-way communication between two programs on a network, identified by IP address + port + protocol.
2. **Why TCP instead of UDP?** Chat needs reliable, ordered delivery. TCP gives acknowledgements, retransmission and ordering; UDP is connectionless and may lose/reorder packets.
3. **What is `AF_INET`?** Address family for IPv4 addressing.
4. **What is `SOCK_STREAM`?** Socket type for a reliable byte-stream, i.e. TCP.
5. **What is a port?** A 16-bit number (0–65535) identifying a particular application/service on a host. We use 5000.
6. **What is binding?** `bind((ip, port))` associates the socket with a local IP and port so clients know where to connect.
7. **What does `listen()` do?** Marks the socket as passive/ready to accept connections and sets the backlog queue size (10 here).
8. **What does `accept()` do?** Blocks until a client connects and returns a new socket for that client plus its address.
9. **What does `connect()` do?** Client-side call that starts the TCP 3-way handshake with the server's IP and port.
10. **Why is threading required?** `accept()` and `recv()` block. Without threads, one client would freeze everyone else. One thread per client lets all be served at once.
11. **How does broadcasting work?** The server stores all client sockets in a dictionary; on a message it loops through them and sends the text to each.
12. **What happens when a client disconnects?** `readline()` returns empty (or raises an error); the thread removes the client from the dictionary, announces "left the chat", logs it, and closes the socket. Other clients continue.
13. **How is the chat log generated?** `ChatLogger` opens `chat_log.txt` in append mode and writes `[date time] text` on each message/event, using a lock for thread safety.
14. **Difference between server and client sockets?** The server has a *listening* socket (bind/listen/accept) and creates a separate *connection* socket per client; a client has one socket that calls `connect()`.
15. **What happens during TCP connection establishment?** Three-way handshake: client sends SYN, server replies SYN-ACK, client sends ACK; then the connection is ESTABLISHED.
16. **How is a TCP connection closed?** With FIN/ACK exchanges (four-way termination), triggered by `shutdown()`/`close()`.
17. **What is `0.0.0.0`?** A special address meaning "all network interfaces", so the server accepts local and LAN connections.
18. **What is `127.0.0.1`?** The loopback address — refers to the same computer.
19. **What is `SO_REUSEADDR`?** Lets the server rebind to the port immediately after restart instead of waiting for TIME_WAIT.
20. **What is `sendall()` vs `send()`?** `send()` may send only part of the data; `sendall()` keeps sending until everything is sent.
21. **Why do we add `\n` to messages?** TCP is a stream with no message boundaries; the newline marks where each message ends.
22. **What is a race condition and how did you avoid it?** Two threads changing shared data at once give wrong results. A `threading.Lock` protects the `clients` dictionary and the log file.
23. **What is an ephemeral port?** A temporary port the OS assigns to the client side of a connection.
24. **Is the chat encrypted?** No — plain text. TLS (`ssl` module) is a future enhancement.
25. **Which OSI layers are involved?** Our protocol = Application; TCP = Transport; IP = Network; Ethernet/Wi-Fi = Data link/Physical. Sockets are the API between Application and Transport.
26. **What are daemon threads?** Threads that don't block program exit; client threads are daemon so shutdown is clean.

---
## PART 8 — PROJECT REPORT CONTENT

### 1. Abstract
This project implements a multi-client chat application based on the client-server model using Python TCP sockets. A multithreaded server accepts several simultaneous client connections, receives messages, and broadcasts them to all connected users. The system supports unique usernames, commands (/users, /help, /time, /quit), join/leave notifications, error handling, and a persistent chat log with date and time stamps. A terminal client and a Tkinter GUI client are provided. The project demonstrates core Computer Networks concepts: TCP/IP, sockets, ports, connection-oriented and reliable communication, multithreading and application-layer protocol design.

### 2. Introduction
Real-time messaging is one of the most common network applications. Such applications rely on the transport layer to carry data between processes on different hosts. Sockets are the programming interface to the TCP/IP stack. This project uses the Python `socket` and `threading` modules to build a working chat system and to understand how network applications communicate.

### 3. Problem Statement
To design and implement a reliable, multi-user text chat application in which several clients connect to a central server over TCP, exchange messages in real time through the server, and have all communication recorded in a log file.

### 4. Objectives
- Implement client-server architecture with TCP sockets.
- Allow multiple simultaneous clients using multithreading.
- Provide server responses and chat commands.
- Maintain a persistent chat log.
- Handle network and user errors gracefully.
- Demonstrate socket programming concepts practically.

### 5. Existing System
Popular systems (WhatsApp, Telegram, Slack, IRC) provide chat using large, complex infrastructures with encryption, databases and cloud servers. Without such a platform, simple local-network messaging is not available, and these systems hide the underlying socket-level details from students. Traditional console tools such as basic `telnet`/`netcat` chat allow only one-to-one communication without usernames, commands or logging.

### 6. Proposed System
A lightweight Python chat system with a central multithreaded TCP server and multiple clients. The server manages usernames, broadcasts messages, answers commands, notifies join/leave events and logs everything. It runs on a single computer or across a LAN with no external libraries, and exposes the working of each socket call clearly.

### 7. Hardware Requirements
- Processor: Dual-core 1.0 GHz or higher
- RAM: 2 GB minimum (4 GB recommended)
- Storage: 100 MB free
- Network: LAN/Wi-Fi adapter (for multi-computer testing)
- Display, keyboard, mouse

### 8. Software Requirements
- OS: Windows 10/11, Linux or macOS
- Python 3.8 or later
- Tkinter (bundled with Python; for GUI)
- Text editor/IDE: VS Code, IDLE or PyCharm
- Terminal / Command Prompt

### 9. Technologies Used
Python 3; `socket` (TCP sockets); `threading` and `Lock`; `datetime`; `re` (username validation); `argparse`; file handling (log file); `tkinter` and `queue` (GUI); TCP/IP protocol suite.

### 10. System Architecture
Client-server architecture (see README Part 2). The server contains: listening socket, accept loop, per-client threads, client dictionary protected by a lock, command processor, broadcaster, logger and admin console. Each client contains: a socket, a sender (user input/GUI) and a receiver thread. Communication uses TCP; messages are newline-terminated UTF-8 text.

### 11. Methodology
1. Study of TCP/IP and socket API. 2. Design of the protocol (handshake, messages, commands). 3. Implementation of the logger. 4. Implementation of the multithreaded server. 5. Implementation of terminal and GUI clients. 6. Error handling and validation. 7. Testing with three simultaneous clients and error scenarios. 8. Documentation.

### 12. Algorithm
**Server**
1. Create TCP socket; set SO_REUSEADDR.
2. Bind to (host, port); listen.
3. Loop: accept a connection; start a new thread for it.
4. In each thread: read the username → validate (format, reserved, duplicate) → if invalid send error and close.
5. Register client in dictionary (under lock); send welcome; broadcast "joined" and user list; log event.
6. Repeat: read a line; if empty → ignore with response; if it starts with "/" → execute command; else log and broadcast "username: message".
7. On disconnect/error: remove client, broadcast "left", log, close socket.
8. On /shutdown: notify clients, close all sockets and the server socket.

**Client**
1. Create TCP socket; connect to (server IP, port). 2. Send username; wait for USERNAME_OK. 3. Start receiver thread to print incoming lines. 4. Main thread reads user input and sends it. 5. On /quit or error, close the socket.

### 13. Implementation
Implemented in four Python files: `server.py` (ChatServer and ClientConnection classes), `chat_logger.py` (ChatLogger), `client.py` (terminal client, connect helper) and `gui_client.py` (Tkinter interface). Thread safety is ensured with locks; GUI updates use a queue to avoid cross-thread Tkinter calls. Messages are framed by newline characters because TCP has no message boundaries.

### 14. Results
The server started and listened on the configured port. Three clients (Shruti, Poonam, Rahul) connected simultaneously and received each other's messages through broadcasting. Commands /users, /time, /help and /quit worked; invalid commands, duplicate and invalid usernames, empty messages and an unreachable server were handled with clear messages. An abruptly closed client was removed without affecting the others. All messages and events were saved with date and time in `chat_logs/chat_log.txt`, which persisted after server shutdown. (Insert screenshots here.)

### 15. Advantages
Simple and easy to understand; no external libraries; supports many clients; reliable delivery through TCP; persistent logs; works on localhost and LAN; modular code; GUI and CLI options.

### 16. Limitations
No encryption or authentication; messages are plain text; one chat room only; no private messaging; thread-per-client limits scalability to a few hundred users; logs are a plain text file; works on a LAN (internet use needs port forwarding/public IP).

### 17. Applications
Classroom/lab messaging, office LAN communication, learning tool for socket programming, base for multiplayer games or remote monitoring/notification systems.

### 18. Future Scope
TLS encryption (`ssl`), user authentication with passwords, private messages (`/msg user text`), multiple chat rooms, file transfer, message history database, `asyncio`/`select` for greater scalability, web or mobile client, emojis and read receipts.

### 19. Conclusion
The project successfully demonstrates a multi-client chat system built with Python TCP sockets. It shows practically how connection-oriented, reliable communication works in client-server networks and how multithreading enables concurrent clients, while keeping the design simple enough to explain and extend.

### 20. References
1. Python Software Foundation, "socket — Low-level networking interface", Python 3 documentation, https://docs.python.org/3/library/socket.html
2. Python Software Foundation, "threading — Thread-based parallelism", https://docs.python.org/3/library/threading.html
3. Python Software Foundation, "tkinter — Python interface to Tcl/Tk", https://docs.python.org/3/library/tkinter.html
4. Forouzan, B. A., *Data Communications and Networking*, McGraw-Hill.
5. Tanenbaum, A. S., Wetherall, D., *Computer Networks*, Pearson.
6. Kurose, J., Ross, K., *Computer Networking: A Top-Down Approach*, Pearson.
7. Python Software Foundation, "Socket Programming HOWTO", https://docs.python.org/3/howto/sockets.html
