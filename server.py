import socket
import threading
import json
import argparse
import os
import time
from pathlib import Path
from datetime import datetime, timezone

# Configurable variables (pika 1)
HOST = '127.0.0.1'      
PORT = 9000            
MAX_CONNECTIONS = 10   # maksimumi i lidhjeve aktive
IDLE_TIMEOUT = 120     # sekonda pa aktivitet -> mbyll lidhjen
STATS_SAVE_INTERVAL = 10
STORAGE_DIR = Path('server_storage')
USERS_FILE = Path('users.json')
MESSAGES_LOG = Path('messages.log')
STATS_FILE = Path('server_stats.txt')

STORAGE_DIR.mkdir(exist_ok=True)
lock = threading.Lock()

clients = {}

if not USERS_FILE.exists():
    USERS_FILE.write_text(json.dumps({
        "device1": {"password": "pass1", "role": "full"},
        "device2": {"password": "pass2", "role": "read"},
        "device3": {"password": "pass3", "role": "read"},
        "device4": {"password": "pass4", "role": "read"}
    }, indent=2))

USERS = json.load(open(USERS_FILE, 'r', encoding='utf-8'))

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def log_message(s):
    ts = now_iso()
    with open(MESSAGES_LOG, 'a', encoding='utf-8') as lf:
        lf.write(f"[{ts}] {s}\n")

def collect_stats():
    with lock:
        return {
            'timestamp': now_iso(),
            'active_connections': len(clients),
            'active_clients': {f"{v['addr'][0]}:{v['addr'][1]}": v['username'] for v in clients.values()},
            'messages_per_client': {v['username']: v['msgs'] for v in clients.values()},
            'total_bytes_received': sum(v['bytes_recv'] for v in clients.values()),
            'total_bytes_sent': sum(v['bytes_sent'] for v in clients.values()),
            'has_sent_request': {v['username']: v['has_sent_request'] for v in clients.values()}
        }

def save_stats_periodically():
    while True:
        time.sleep(STATS_SAVE_INTERVAL)
        with open(STATS_FILE, 'w', encoding='utf-8') as sf:
            json.dump(collect_stats(), sf, indent=2)

def receive_all(conn, n):
    data = b''
    while len(data) < n:
        part = conn.recv(n - len(data))
        if not part:
            break
        data += part
    return data

def receive_line(conn, timeout=None):
    chunks = []
    conn.settimeout(None if timeout is None else timeout)
    while True:
        part = conn.recv(4096)
        if not part:
            return b''.join(chunks)
        chunks.append(part)
        if b'\n' in part:
            data = b''.join(chunks)
            line, _, rest = data.partition(b'\n')
            return line

def send_response(conn, data_bytes):
    try:
        conn.sendall(data_bytes)
        with lock:
            if conn in clients:
                clients[conn]['bytes_sent'] += len(data_bytes)
    except Exception:
        pass

def handle_read(f):
    p = STORAGE_DIR / f
    if not p.exists(): return "File not found."
    try:
        return p.read_text(encoding='utf-8')
    except Exception as e:
        return f"Error reading file: {e}"

def handle_list():
    return '\n'.join(sorted([x.name for x in STORAGE_DIR.iterdir() if x.is_file()])) or "(empty)"

def handle_delete(f):
    p = STORAGE_DIR / f
    if not p.exists(): return "File not found."
    try:
        p.unlink()
        return "Deleted."
    except Exception as e:
        return f"Delete failed: {e}"

def handle_search(kw):
    return '\n'.join(sorted([f.name for f in STORAGE_DIR.iterdir() if kw.lower() in f.name.lower()])) or "(no matches)"

def handle_info(f):
    p = STORAGE_DIR / f
    if not p.exists(): return "File not found."
    s = p.stat()
    return json.dumps({'size': s.st_size, 'created': s.st_ctime, 'modified': s.st_mtime}, indent=2)

def handle_upload(conn, filename):

    send_response(conn, b"READY_META\n")

    try:
        meta_line = receive_line(conn, timeout=10)
        if not meta_line:
            return "Upload failed: no metadata received."
        meta = json.loads(meta_line.decode())
        size = int(meta.get('size', 0))
      
        send_response(conn, b"READY_DATA\n")
        file_bytes = receive_all(conn, size)
        if len(file_bytes) < size:
            return f"Upload failed: expected {size} bytes, got {len(file_bytes)} bytes."
        safe_name = Path(filename).name
        path = STORAGE_DIR / safe_name
        with open(path, 'wb') as f:
            f.write(file_bytes)
        return f"Uploaded {safe_name} ({size} bytes)"
    except Exception as e:
        return f"Upload error: {e}"

def handle_download(conn, filename):
    p = STORAGE_DIR / filename
    if not p.exists():
        send_response(conn, b"ERROR: File not found.\n")
        return
    size = p.stat().st_size
    send_response(conn, f"FILEMETA {json.dumps({'filename': filename, 'size': size})}\n".encode())
    try:
        ready = receive_line(conn, timeout=10)
        if not ready or ready.strip().upper() != b'READY':
            send_response(conn, b"ERROR: download aborted by client\n")
            return
        with open(p, 'rb') as f:
            data = f.read()
            send_response(conn, data)
    except Exception as e:
        send_response(conn, f"ERROR during download: {e}\n".encode())

def client_thread(conn, addr):
 
    conn.settimeout(1.0)
    with lock:
        clients[conn] = {
            'addr': addr,
            'username': f"{addr[0]}:{addr[1]}",
            'role': 'read',
            'last_active': time.time(),
            'msgs': 0,
            'bytes_recv': 0,
            'bytes_sent': 0,
            'has_sent_request': False  # <-- Flag per me kontrollu nese klienti ka bo tpakten nje kerkese
        }
    try:
        send_response(conn, b"HELLO? Send: HELLO user pass\n")
        buf = b''
        auth = False
        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    break
            except socket.timeout:
                continue
            buf += data
            if b'\n' in buf:
                line, _, buf = buf.partition(b'\n')
                parts = line.decode().strip().split()
                if len(parts) == 3 and parts[0].upper() == 'HELLO':
                    u, p = parts[1], parts[2]
                    if u in USERS and USERS[u]['password'] == p:
                        with lock:
                            if conn in clients:
                                clients[conn]['username'] = u
                                clients[conn]['role'] = USERS[u]['role']
                        send_response(conn, f"WELCOME {u} ({USERS[u]['role']})\n".encode())
                        auth = True
                        break
                    else:
                        send_response(conn, b"AUTH_FAILED\n")
                        conn.close()
                        return
        if not auth:
            conn.close()
            return

        while True:
            try:
                data = conn.recv(4096)
            except socket.timeout:
                with lock:
                    last = clients.get(conn, {}).get('last_active', time.time())
                if time.time() - last > IDLE_TIMEOUT:
                    send_response(conn, b"IDLE_TIMEOUT\n")
                    break
                continue
            if not data:
                break

            with lock:
                if conn in clients:
                    clients[conn]['msgs'] += 1
                    clients[conn]['last_active'] = time.time()
                    clients[conn]['has_sent_request'] = True

            text = data.decode(errors='ignore').strip()


            if text.upper() == 'STATS':
                s = json.dumps(collect_stats(), indent=2)
                send_response(conn, s.encode() + b'\n')
                continue

            if text.startswith('/'):
                parts = text.split()
                cmd = parts[0]
                args = parts[1:]
                with lock:
                    role = clients[conn]['role']
               
                if role != 'full' and cmd not in ['/list', '/read', '/search', '/info']:
                    send_response(conn, b"ERROR: permission denied\n")
                    continue

                if cmd == '/list':
                    resp = handle_list()
                    send_response(conn, resp.encode() + b'\n')
                elif cmd == '/read':
                    if not args:
                        send_response(conn, b"Usage: /read <filename>\n")
                    else:
                        resp = handle_read(args[0])
                        send_response(conn, resp.encode() + b'\n')
                elif cmd == '/delete':
                    if not args:
                        send_response(conn, b"Usage: /delete <filename>\n")
                    else:
                        resp = handle_delete(args[0])
                        send_response(conn, resp.encode() + b'\n')
                elif cmd == '/search':
                    if not args:
                        send_response(conn, b"Usage: /search <keyword>\n")
                    else:
                        resp = handle_search(args[0])
                        send_response(conn, resp.encode() + b'\n')
                elif cmd == '/info':
                    if not args:
                        send_response(conn, b"Usage: /info <filename>\n")
                    else:
                        resp = handle_info(args[0])
                        send_response(conn, resp.encode() + b'\n')
                elif cmd == '/upload':
                    if not args:
                        send_response(conn, b"Usage: /upload <filename>\n")
                    else:
                        # handle upload protocol
                        resp = handle_upload(conn, args[0])
                        send_response(conn, resp.encode() + b'\n')
                elif cmd == '/download':
                    if not args:
                        send_response(conn, b"Usage: /download <filename>\n")
                    else:
                        handle_download(conn, args[0])
                else:
                    send_response(conn, b"Unknown command\n")
            else:
                # plain text -> echo + log
                send_response(conn, f"ECHO: {text}\n".encode())
                log_message(f"{clients[conn]['username']}@{addr}: {text}")

    except Exception as e:
        print('Error in client thread:', e)
    finally:
        with lock:
            if conn in clients:
                del clients[conn]
        try:
            conn.close()
        except:
            pass

def accept_loop(sock):
    while True:
        conn, addr = sock.accept()
        with lock:
            if len(clients) >= MAX_CONNECTIONS:
                try:
                    conn.sendall(b"SERVER_BUSY\n")
                except Exception:
                    pass
                conn.close()
                continue
        t = threading.Thread(target=client_thread, args=(conn, addr), daemon=True)
        t.start()

def admin_console():
       while True:
        try:
            cmd = input()
        except EOFError:
            break
        if cmd.upper() == 'STATS':
            print(json.dumps(collect_stats(), indent=2))
        elif cmd.upper() == 'QUIT':
            print("Shutting down.")
            os._exit(0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=HOST)
    parser.add_argument('--port', default=PORT, type=int)
    args = parser.parse_args()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((args.host, args.port))
    s.listen()
    print(f"Server running on {args.host}:{args.port}")
    # start stats saver and admin console
    threading.Thread(target=save_stats_periodically, daemon=True).start()
    threading.Thread(target=admin_console, daemon=True).start()
    accept_loop(s)

if __name__ == '__main__':
    main()

