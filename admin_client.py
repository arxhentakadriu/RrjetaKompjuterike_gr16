import socket
import argparse
import json
import os
import time


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
    if b'WELCOME' in welcome:
        break

welcome_clean = welcome.decode(errors='ignore').replace("\r", "").strip()
print(welcome_clean)

if "full" in welcome_clean.lower():
    role = "full"
else:
    role = "read"

print(f"Assigned role: {role}")


def receive_line(sock, timeout=10):
    sock.settimeout(timeout)
    data = b''
    while True:
        part = sock.recv(4096)
        if not part:
            break
        data += part
        if b'\n' in data:
            line, _, rest = data.partition(b'\n')
            return line
    return data


try:
    while True:
        try:
            cmd = input("ADMIN> ").strip()
            if not cmd:
                continue


            if cmd.startswith('/upload'):
                parts = cmd.split(maxsplit=1)
                if len(parts) < 2:
                    print("Përdorimi: /upload <file>")
                    continue
                path = parts[1]
                if not os.path.exists(path):
                    print("File nuk ekziston.")
                    continue
                with open(path, 'rb') as f:
                    data = f.read()
                filename = os.path.basename(path)

                s.sendall(f"/upload {filename}\n".encode())

                ready = receive_line(s)
                if not ready or b"READY_META" not in ready:
                    print("Server nuk pranoi upload (no READY_META). Response:", ready)
                    continue

                meta = json.dumps({'filename': filename, 'size': len(data)})
                s.sendall((meta + '\n').encode())

                ready2 = receive_line(s)
                if not ready2 or b"READY_DATA" not in ready2:
                    print("Server nuk gjeti READY_DATA. Response:", ready2)
                    continue

                s.sendall(data)

                final = s.recv(4096)
                if final:
                    print(final.decode(errors='ignore'))


            elif cmd.startswith('/download'):
                parts = cmd.split(maxsplit=1)
                if len(parts) < 2:
                    print("Përdorimi: /download <filename>")
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
                to_read = size
                while len(received) < to_read:
                    chunk = s.recv(min(4096, to_read - len(received)))
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
                start_time = time.time()
                data = b''

                while True:
                    if time.time() - start_time > timeout:
                        break
                    try:
                        chunk = s.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                        if len(chunk) < 4096:
                            break
                    except BlockingIOError:
                        time.sleep(0.05)
                        continue

                if data:
                    print(data.decode(errors='ignore'))

        except KeyboardInterrupt:
            break

finally:
    s.close()
