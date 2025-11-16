import socket, argparse, os, json, time

parser = argparse.ArgumentParser()
parser.add_argument('--host', required=True)
parser.add_argument('--port', required=True, type=int)
parser.add_argument('--user', required=True)
parser.add_argument('--password', required=True)
args = parser.parse_args()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((args.host, args.port))
s.sendall(f"HELLO {args.user} {args.password}\n".encode())

welcome = b""
while True:
    chunk = s.recv(4096)
    if not chunk:
        break
    welcome += chunk
    if b'WELCOME' in welcome or b'AUTH_FAILED' in welcome:
        break

welcome_clean = welcome.decode(errors='ignore').replace("\r", "").strip()
print(welcome_clean)

role = "full" if "full" in welcome_clean.lower() else "read"
print(f"Assigned role: {role}")

def receive_line(sock, timeout=2.0):
    sock.settimeout(timeout)
    data = b''
    while True:
        try:
            part = sock.recv(4096)
        except socket.timeout:
            break
        if not part:
            break
        data += part
        if b'\n' in data:
            line, _, _ = data.partition(b'\n')
            return line
    return data

try:
    while True:
        cmd = input("> ").strip()
        if not cmd:
            continue

        if cmd.startswith(('/upload', '/delete', '/download')) and role != 'full':
            print("Read-only client — nuk ke leje për këtë komandë.")
            continue

        if cmd.startswith('/upload') and role == 'full':
            parts = cmd.split(maxsplit=1)
            if len(parts) != 2:
                print("Usage: /upload <filename>")
                continue
            filename = parts[1]
            if not os.path.isfile(filename):
                print("File nuk ekziston!")
                continue
            filesize = os.path.getsize(filename)
            s.sendall(f"/upload {os.path.basename(filename)}\n".encode())
            ready = receive_line(s)
            if not ready or b"READY_META" not in ready:
                print("Server nuk pranoi upload (no READY_META). Response:", ready)
                continue
            meta = json.dumps({"filename": os.path.basename(filename), "size": filesize})
            s.sendall((meta + '\n').encode())
            ready2 = receive_line(s)
            if not ready2 or b"READY_DATA" not in ready2:
                print("Server nuk gjeti READY_DATA. Response:", ready2)
                continue
            with open(filename, 'rb') as f:
                s.sendall(f.read())
            final = receive_line(s)
            if final:
                print(final.decode(errors='ignore'))
            continue

        if cmd.startswith('/download') and role == 'full':
            parts = cmd.split(maxsplit=1)
            if len(parts) != 2:
                print("Usage: /download <filename>")
                continue
            filename = parts[1]
            s.sendall(f"/download {filename}\n".encode())
            meta_line = receive_line(s)
            if not meta_line:
                print("No response from server.")
                continue
            meta_line = meta_line.decode(errors='ignore')
            if meta_line.startswith("ERROR"):
                print(meta_line)
                continue
            if not meta_line.startswith("FILEMETA"):
                print("Unexpected response:", meta_line)
                continue
            _, _, j = meta_line.partition(' ')
            meta = json.loads(j)
            size = int(meta.get('size', 0))
            s.sendall(b"READY\n")
            received = b''
            while len(received) < size:
                chunk = s.recv(min(4096, size - len(received)))
                if not chunk:
                    break
                received += chunk
            with open(filename, 'wb') as f:
                f.write(received)
            print(f"Downloaded {filename} ({len(received)} bytes)")
            continue

        s.sendall((cmd + '\n').encode())
        timeout = 0.5 if role == "full" else 2.0
        start_time = time.time()
        data = b''
        while True:
            if time.time() - start_time > timeout:
                break
            try:
                chunk = s.recv(4096)
            except BlockingIOError:
                time.sleep(0.05)
                continue
            if not chunk:
                break
            data += chunk
            if len(chunk) < 4096:
                break
        if data:
            print(data.decode(errors='ignore'))

except KeyboardInterrupt:
    print("\nClosing connection...")
finally:
    s.close()
