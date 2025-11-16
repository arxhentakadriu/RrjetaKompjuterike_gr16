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
    if not chunk: break
    welcome += chunk
    if b'WELCOME' in welcome: break

welcome_clean = welcome.decode(errors='ignore').replace("\r","").strip()
print(welcome_clean)
role = "full" if "full" in welcome_clean.lower() else "read"
print(f"Assigned role: {role}")

def receive_line(sock, timeout=10):
    sock.settimeout(timeout)
    data = b''
    while True:
        part = sock.recv(4096)
        if not part: break
        data += part
        if b'\n' in data:
            line, _, _ = data.partition(b'\n')
            return line
    return data

try:
    while True:
        cmd = input("> ").strip()
        if not cmd: continue

        if cmd.startswith(('/upload','/delete','/download')) and role != 'full':
            print("Read-only client — nuk ke leje për këtë komandë.")
            continue

        if cmd.startswith('/upload') and role=='full':
            parts = cmd.split(maxsplit=1)
            if len(parts)!=2: continue
            path = parts[1]
            if not os.path.exists(path): continue
            filename = os.path.basename(path)
            data = open(path,'rb').read()
            s.sendall(f"/upload {filename}\n".encode())
            ready = receive_line(s)
            if ready and b"READY_META" in ready:
                s.sendall(json.dumps({'filename':filename,'size':len(data)}).encode()+b'\n')
                ready2 = receive_line(s)
                if ready2 and b"READY_DATA" in ready2:
                    s.sendall(data)
                    final = s.recv(4096)
                    if final: print(final.decode(errors='ignore'))
        elif cmd.startswith('/download') and role=='full':
            parts = cmd.split(maxsplit=1)
            if len(parts)!=2: continue
            filename = parts[1]
            s.sendall(cmd.encode()+b'\n')
            meta_line = receive_line(s)
            if not meta_line: continue
            meta_line = meta_line.decode(errors='ignore')
            if meta_line.startswith("ERROR"): print(meta_line); continue
            _, _, j = meta_line.partition(' ')
            meta = json.loads(j)
            size = int(meta.get('size',0))
            s.sendall(b"READY\n")
            received = b''
            to_read = size
            while len(received)<to_read:
                chunk = s.recv(min(4096,to_read-len(received)))
                if not chunk: break
                received += chunk
            with open(filename,'wb') as f: f.write(received)
            print(f"Downloaded {filename} ({len(received)} bytes)")
        else:
            s.sendall((cmd+'\n').encode())
            timeout = 0.5 if role=="full" else 2.0
            s.settimeout(timeout)
            try: resp = s.recv(8192)
            except socket.timeout:
                print("(Server response delayed...)"); continue
            if not resp: print("Server closed connection"); break
            print(resp.decode(errors='ignore'))
except KeyboardInterrupt:
    pass
finally:
    s.close()
