import socket, argparse, json, os, time

parser = argparse.ArgumentParser()
parser.add_argument('--host', required=True)
parser.add_argument('--port', required=True, type=int)
parser.add_argument('--user', required=True)
parser.add_argument('--password', required=True)
args = parser.parse_args()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((args.host, args.port))
s.sendall(f"HELLO {args.user} {args.password}\n".encode())
welcome = s.recv(4096).decode()
print(welcome.strip())

role = "full" if "full" in welcome.lower() else "read"
print(f"Assigned role: {role}")

def receive_line(sock, timeout=20):
    sock.settimeout(timeout)
    data = b''
    while True:
        try:
            part = sock.recv(4096)
        except socket.timeout:
            return None
        if not part:
            break
        data += part
        if b'\n' in data:
            line, _, rest = data.partition(b'\n')
            return line
    return data

try:
    while True:
        cmd = input("ADMIN> ").strip()
        if not cmd:
            continue

        if cmd.startswith('/upload'):
            if role != 'full':
                print("Read-only client: nuk ke leje për upload.")
                continue

            parts = cmd.split(maxsplit=1)
            if len(parts) < 2:
                print("Përdorimi: /upload <file>")
                continue
            path = parts[1].strip('"') 
            if not os.path.exists(path):
                print("File nuk ekziston:", path)
                continue

            filename = os.path.basename(path)
            filesize = os.path.getsize(path)
            print(f"Preparing to upload {filename} ({filesize} bytes)")

            s.sendall(f"/upload {filename}\n".encode())
            print("Sent /upload command, waiting READY_META...")

            ready = receive_line(s)
            if not ready or b"READY_META" not in ready:
                print("Server nuk pranoi upload (no READY_META). Response:", ready)
                continue
            print("Received READY_META")

            meta = json.dumps({'filename': filename, 'size': len(data)})
            s.sendall((meta + '\n').encode())
            print("Sent metadata, waiting READY_DATA...")

            ready2 = receive_line(s)
            if not ready2 or b"READY_DATA" not in ready2:
                print("Server nuk gjeti READY_DATA. Response:", ready2)
                continue
            print("Received READY_DATA, sending file...")

            with open(path, 'rb') as f:
                s.sendall(f.read())
            print(f"Upload i kryer: {filename}")

            final = receive_line(s, timeout=10)
            if final:
                print("Server:", final.decode(errors='ignore'))

        elif cmd.startswith('/download'):
            parts = cmd.split(maxsplit=1)
            if len(parts) < 2:
                print("Përdorimi: /download <filename>")
                continue
            filename = parts[1].strip('"')
            s.sendall(f"/download {filename}\n".encode())
            meta_line = receive_line(s)
            if not meta_line:
                print("No response from server.")
                continue
            meta_line = meta_line.decode()
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

            if len(received) < size:
                print(f"Download incomplete: got {len(received)} of {size} bytes")
            else:
                out_path = filename
                with open(out_path, 'wb') as f:
                    f.write(received)
                print(f"Downloaded {out_path} ({len(received)} bytes)")

        else:
            s.sendall((cmd + '\n').encode())
            timeout = 0.5 if role == "full" else 2.0
            s.settimeout(timeout)
            try:
                resp = s.recv(8192)
                if resp:
                    print(resp.decode(errors='ignore'))
            except socket.timeout:
                print("(Server response delayed...)")

except KeyboardInterrupt:
    print("\nClosing connection...")
finally:
    s.close()
